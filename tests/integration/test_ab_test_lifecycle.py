"""
Integration test: Full A/B test lifecycle.

generate_copy → design_ab_test → start_ab_test → log_metrics (many)
→ check_ab_test → conclude_ab_test → verify learning recommendation

Note: design_ab_test computes a sample size of 1600 for open_rate
(statistically correct for detecting 20% relative lift). For integration
testing we write the plan directly with a small sample_size so the test
can run with ~10 metric entries instead of thousands.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.copy_tools import generate_copy, save_copy_variant
from tools.metrics_tools import log_metrics
from tools.analysis_tools import design_ab_test, save_learning
from tools.ab_test_tools import start_ab_test, check_ab_test, conclude_ab_test, list_active_tests


def _create_campaign_with_variants(tmp_data_dir, campaign_name="ab-lifecycle"):
    """Helper: create a campaign with 2 variants and return campaign_id."""
    call_tool(generate_copy, brief="Test email campaign", channel="email",
              num_variants=2, campaign_name=campaign_name)

    call_tool(save_copy_variant, campaign_id=campaign_name, variant_id="v1",
              channel="email", content="Control copy: Professional tone.",
              subject_line="Important Update", cta="Learn More", tone="professional")

    call_tool(save_copy_variant, campaign_id=campaign_name, variant_id="v2",
              channel="email", content="Treatment copy: Playful tone!",
              subject_line="You Won't Believe This!", cta="Check It Out", tone="playful")

    return campaign_name


def _write_small_ab_plan(tmp_data_dir, campaign_id, sample_per_variant=10):
    """Write an ab_test.json plan with a small sample_size for testing."""
    plan = {
        "campaign_id": campaign_id,
        "channel": "email",
        "hypothesis": "Playful tone will have higher open rates",
        "variable_tested": "tone",
        "control": {"description": "Professional tone", "variant_id": "control"},
        "treatment": {"description": "Playful tone", "variant_id": "treatment"},
        "primary_metric": "open_rate",
        "metrics_to_track": ["open_rate", "click_rate"],
        "sample_size": {"per_variant": sample_per_variant, "total": sample_per_variant * 2},
        "status": "designed",
    }
    plan_path = tmp_data_dir / "campaigns" / campaign_id / "ab_test.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")


def _log_many_metrics(campaign_id, variant_id, metric_type, values):
    """Log multiple metric entries for a variant (one per value)."""
    for i, val in enumerate(values):
        call_tool(log_metrics, campaign_id=campaign_id, variant_id=variant_id,
                  metric_type=metric_type, value=val,
                  date=f"2026-04-{(i+1):02d}")


class TestAbTestLifecycle:
    """End-to-end: campaign → A/B test → start → metrics → check → conclude."""

    def test_full_ab_test_with_winner(self, tmp_data_dir):
        campaign_id = _create_campaign_with_variants(tmp_data_dir)

        # Write plan with small sample_size so 10 entries suffices
        _write_small_ab_plan(tmp_data_dir, campaign_id, sample_per_variant=5)

        # Start the test
        result = call_tool(start_ab_test, campaign_id=campaign_id, test_id="test-tone-001")
        assert "COLLECTING" in result
        assert "test-tone-001" in result

        # Verify test is listed as active
        active = call_tool(list_active_tests)
        assert "test-tone-001" in active

        # Log metrics. Use extreme differences so the z-test is significant.
        # Control: very low open rates (mean ~0.05)
        control_rates = [0.04, 0.06, 0.05, 0.04, 0.06, 0.05, 0.04, 0.06, 0.05, 0.05]
        # Treatment: very high open rates (mean ~0.90)
        treatment_rates = [0.88, 0.92, 0.90, 0.89, 0.91, 0.90, 0.88, 0.92, 0.91, 0.89]

        _log_many_metrics(campaign_id, "control", "open_rate", control_rates)
        _log_many_metrics(campaign_id, "treatment", "open_rate", treatment_rates)

        # Check the test — should detect significant difference
        result = call_tool(check_ab_test, campaign_id=campaign_id, test_id="test-tone-001")
        assert "DECIDED" in result or "WINNER" in result

        # Verify state file shows DECIDED
        state = json.loads(
            (tmp_data_dir / "campaigns" / campaign_id / "ab_test_state.json").read_text()
        )
        assert state["state"] == "DECIDED"
        assert state["winner"] is not None

        # Conclude the test
        result = call_tool(conclude_ab_test, campaign_id=campaign_id, test_id="test-tone-001")
        assert "COMPLETED" in result
        assert "learning" in result.lower()

        # Verify state is COMPLETED
        state = json.loads(
            (tmp_data_dir / "campaigns" / campaign_id / "ab_test_state.json").read_text()
        )
        assert state["state"] == "COMPLETED"

        # Verify winner recorded in state result
        assert state["result"]["verdict"].startswith("winner_")
        assert state["result"]["winner_variant"] == "treatment"

        # Verify learning recommendation was generated
        assert state.get("learning_recommendation") is not None
        assert state["learning_recommendation"].get("learning") is not None

    def test_insufficient_data_then_winner(self, tmp_data_dir):
        """First check with too few metrics → insufficient_data,
        then add more → winner detected."""
        campaign_id = _create_campaign_with_variants(tmp_data_dir, "ab-insuff")
        _write_small_ab_plan(tmp_data_dir, campaign_id, sample_per_variant=8)

        call_tool(start_ab_test, campaign_id=campaign_id)

        # Log only 3 metrics per variant (below the 5-sample minimum check)
        _log_many_metrics(campaign_id, "control", "open_rate", [0.05, 0.06, 0.04])
        _log_many_metrics(campaign_id, "treatment", "open_rate", [0.90, 0.91, 0.89])

        result = call_tool(check_ab_test, campaign_id=campaign_id)
        assert "insufficient" in result.lower() or "WAITING" in result

        # Now add enough data to cross the minimum sample threshold
        _log_many_metrics(campaign_id, "control", "open_rate",
                          [0.05, 0.04, 0.06, 0.05, 0.04, 0.06, 0.05])
        _log_many_metrics(campaign_id, "treatment", "open_rate",
                          [0.90, 0.92, 0.88, 0.91, 0.90, 0.89, 0.91])

        result = call_tool(check_ab_test, campaign_id=campaign_id)
        assert "DECIDED" in result or "winner" in result.lower()

    def test_conclude_saves_learning_recommendation(self, tmp_data_dir):
        """conclude_ab_test generates a learning recommendation that can be
        saved via save_learning."""
        campaign_id = _create_campaign_with_variants(tmp_data_dir, "ab-learn")
        _write_small_ab_plan(tmp_data_dir, campaign_id, sample_per_variant=5)
        call_tool(start_ab_test, campaign_id=campaign_id)

        # Strongly significant data
        _log_many_metrics(campaign_id, "control", "open_rate",
                          [0.03, 0.04, 0.03, 0.05, 0.04, 0.03, 0.04, 0.05, 0.03, 0.04])
        _log_many_metrics(campaign_id, "treatment", "open_rate",
                          [0.85, 0.87, 0.86, 0.88, 0.85, 0.87, 0.86, 0.88, 0.85, 0.87])

        call_tool(check_ab_test, campaign_id=campaign_id)
        call_tool(conclude_ab_test, campaign_id=campaign_id)

        # Read the learning recommendation from state
        state = json.loads(
            (tmp_data_dir / "campaigns" / campaign_id / "ab_test_state.json").read_text()
        )
        rec = state["learning_recommendation"]

        # Save it as an actual playbook learning
        result = call_tool(
            save_learning,
            category=rec["category"],
            learning=rec["learning"],
            evidence=rec["evidence"],
            confidence=rec["confidence"],
        )
        assert "saved" in result.lower()

        # Verify it appears in the playbook
        playbook = json.loads((tmp_data_dir / "playbook.json").read_text())
        found = [l for l in playbook["learnings"]
                 if "tone" in l["learning"].lower()]
        assert len(found) >= 1

    def test_test_no_longer_active_after_conclude(self, tmp_data_dir):
        """After concluding, list_active_tests should not include this test."""
        campaign_id = _create_campaign_with_variants(tmp_data_dir, "ab-done")
        _write_small_ab_plan(tmp_data_dir, campaign_id, sample_per_variant=5)
        call_tool(start_ab_test, campaign_id=campaign_id)

        _log_many_metrics(campaign_id, "control", "open_rate",
                          [0.02, 0.03, 0.02, 0.03, 0.02, 0.03, 0.02, 0.03, 0.02, 0.03])
        _log_many_metrics(campaign_id, "treatment", "open_rate",
                          [0.90, 0.91, 0.89, 0.90, 0.91, 0.90, 0.89, 0.90, 0.91, 0.90])

        call_tool(check_ab_test, campaign_id=campaign_id)
        call_tool(conclude_ab_test, campaign_id=campaign_id)

        active = call_tool(list_active_tests)
        assert campaign_id not in active or "No active" in active

    def test_design_ab_test_creates_plan_file(self, tmp_data_dir):
        """design_ab_test should create ab_test.json in the campaign directory."""
        campaign_id = _create_campaign_with_variants(tmp_data_dir, "ab-design")

        result = call_tool(
            design_ab_test,
            campaign_id=campaign_id,
            hypothesis="Numbers in subject lines increase open rates",
            variable="subject_line_style",
            variants_description="Control: No numbers. Treatment: Includes a number.",
        )
        assert campaign_id in result

        plan_path = tmp_data_dir / "campaigns" / campaign_id / "ab_test.json"
        assert plan_path.exists()
        plan = json.loads(plan_path.read_text())
        assert plan["hypothesis"] == "Numbers in subject lines increase open rates"
        assert plan["variable_tested"] == "subject_line_style"
        assert plan["primary_metric"] == "open_rate"
