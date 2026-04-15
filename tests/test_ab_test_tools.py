"""
Tests for tools/ab_test_tools.py — A/B test lifecycle state machine.

Requires tmp_data_dir fixture for monkeypatched paths.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.ab_test_tools import (
    check_ab_test,
    conclude_ab_test,
    list_active_tests,
    start_ab_test,
)


# =========================================================================
# Helpers — seed an ab_test.json plan for start_ab_test
# =========================================================================

def _write_ab_plan(data_dir, campaign_id, **overrides):
    """Write a minimal ab_test.json plan file."""
    plan = {
        "hypothesis": "Treatment outperforms control on open_rate",
        "variable_tested": "subject_line",
        "control": {"variant_id": "v1", "description": "Control variant"},
        "treatment": {"variant_id": "v2", "description": "Treatment variant"},
        "primary_metric": "open_rate",
        "metrics_to_track": ["open_rate", "click_rate"],
        "sample_size": {"per_variant": 100},
        **overrides,
    }
    path = data_dir / "campaigns" / campaign_id / "ab_test.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def _add_metrics(data_dir, campaign_id, variant_id, metric_type, values):
    """Append metric entries to a campaign's metrics.json."""
    path = data_dir / "campaigns" / campaign_id / "metrics.json"
    if path.exists():
        metrics = json.loads(path.read_text())
    else:
        metrics = []
    for i, v in enumerate(values):
        metrics.append({
            "variant_id": variant_id,
            "metric_type": metric_type,
            "value": v,
            "date": f"2026-04-{(i+1):02d}",
            "notes": "",
            "logged_at": f"2026-04-{(i+1):02d}T12:00:00",
        })
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


# =========================================================================
# start_ab_test
# =========================================================================

class TestStartAbTest:
    def test_starts_test_transitions_to_collecting(self, seed_campaign, tmp_data_dir):
        _write_ab_plan(tmp_data_dir, seed_campaign)
        result = call_tool(start_ab_test, seed_campaign, "my-test-1")
        assert "COLLECTING" in result
        assert "my-test-1" in result

        # Verify state file was created
        state_path = tmp_data_dir / "campaigns" / seed_campaign / "ab_test_state.json"
        state = json.loads(state_path.read_text())
        assert state["state"] == "COLLECTING"
        assert state["test_id"] == "my-test-1"

    def test_nonexistent_campaign_returns_error(self, tmp_data_dir):
        result = call_tool(start_ab_test, "no-such-campaign")
        assert "Error" in result

    def test_no_plan_returns_error(self, seed_campaign, tmp_data_dir):
        result = call_tool(start_ab_test, seed_campaign)
        assert "Error" in result
        assert "No A/B test plan" in result

    def test_already_active_test_returns_error(self, seed_ab_test, tmp_data_dir):
        """An already COLLECTING test should block a new start."""
        campaign_id, test_id = seed_ab_test
        _write_ab_plan(tmp_data_dir, campaign_id)
        result = call_tool(start_ab_test, campaign_id)
        assert "Error" in result
        assert "already active" in result

    def test_state_history_has_designed_deploying_collecting(self, seed_campaign, tmp_data_dir):
        _write_ab_plan(tmp_data_dir, seed_campaign)
        call_tool(start_ab_test, seed_campaign, "hist-test")
        state = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "ab_test_state.json").read_text()
        )
        states = [h["state"] for h in state["state_history"]]
        assert "DESIGNED" in states
        assert "DEPLOYING" in states
        assert "COLLECTING" in states

    def test_auto_generates_test_id(self, seed_campaign, tmp_data_dir):
        _write_ab_plan(tmp_data_dir, seed_campaign)
        result = call_tool(start_ab_test, seed_campaign)
        assert "test-" in result

    def test_sets_next_check_at(self, seed_campaign, tmp_data_dir):
        _write_ab_plan(tmp_data_dir, seed_campaign)
        call_tool(start_ab_test, seed_campaign, "check-test")
        state = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "ab_test_state.json").read_text()
        )
        assert state["next_check_at"] is not None


# =========================================================================
# check_ab_test
# =========================================================================

class TestCheckAbTest:
    def test_no_metrics_transitions_to_waiting(self, seed_campaign, tmp_data_dir):
        """With no metrics, check should move to WAITING."""
        _write_ab_plan(tmp_data_dir, seed_campaign)
        call_tool(start_ab_test, seed_campaign, "check-1")
        # Remove metrics file to simulate no data
        metrics_path = tmp_data_dir / "campaigns" / seed_campaign / "metrics.json"
        if metrics_path.exists():
            metrics_path.unlink()

        result = call_tool(check_ab_test, seed_campaign)
        assert "No metrics found" in result or "WAITING" in result

    def test_insufficient_samples(self, seed_campaign, tmp_data_dir):
        """With fewer than 5 samples per variant, should return insufficient."""
        _write_ab_plan(tmp_data_dir, seed_campaign)
        call_tool(start_ab_test, seed_campaign, "insuff-test")

        # Clear existing metrics, add just a few
        metrics_path = tmp_data_dir / "campaigns" / seed_campaign / "metrics.json"
        metrics_path.write_text("[]", encoding="utf-8")
        _add_metrics(tmp_data_dir, seed_campaign, "v1", "open_rate", [0.2, 0.3])
        _add_metrics(tmp_data_dir, seed_campaign, "v2", "open_rate", [0.25, 0.35])

        result = call_tool(check_ab_test, seed_campaign)
        assert "Insufficient" in result or "insufficient" in result

    def test_significant_result_transitions_to_decided(self, seed_campaign, tmp_data_dir):
        """With enough data showing a clear winner, should transition to DECIDED."""
        _write_ab_plan(tmp_data_dir, seed_campaign, sample_size={"per_variant": 10})
        call_tool(start_ab_test, seed_campaign, "sig-test")

        # Clear and add significant differences
        (tmp_data_dir / "campaigns" / seed_campaign / "metrics.json").write_text("[]")
        _add_metrics(tmp_data_dir, seed_campaign, "v1", "open_rate", [0.10] * 20)  # 10% open rate
        _add_metrics(tmp_data_dir, seed_campaign, "v2", "open_rate", [0.50] * 20)  # 50% open rate

        result = call_tool(check_ab_test, seed_campaign)
        state = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "ab_test_state.json").read_text()
        )
        assert state["state"] == "DECIDED"
        assert state["winner"] is not None
        assert "winner" in result.lower() or "DECIDED" in result

    def test_wrong_state_returns_error(self, tmp_data_dir):
        """check_ab_test should only work on COLLECTING/WAITING tests."""
        # Create a completed test state manually
        campaign_id = "completed-test"
        campaign_dir = tmp_data_dir / "campaigns" / campaign_id
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": campaign_id, "channel": "email", "status": "active"
        }))
        state = {"state": "COMPLETED", "test_id": "t1"}
        (campaign_dir / "ab_test_state.json").write_text(json.dumps(state))

        result = call_tool(check_ab_test, campaign_id)
        assert "Error" in result

    def test_records_check_in_history(self, seed_campaign, tmp_data_dir):
        _write_ab_plan(tmp_data_dir, seed_campaign, sample_size={"per_variant": 10})
        call_tool(start_ab_test, seed_campaign, "hist-check")
        # Use existing metrics from seed
        call_tool(check_ab_test, seed_campaign)

        state = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "ab_test_state.json").read_text()
        )
        assert len(state["checks_performed"]) >= 1

    def test_test_id_mismatch_returns_error(self, seed_ab_test, tmp_data_dir):
        campaign_id, test_id = seed_ab_test
        result = call_tool(check_ab_test, campaign_id, "wrong-test-id")
        assert "Error" in result
        assert "mismatch" in result.lower()


# =========================================================================
# conclude_ab_test
# =========================================================================

class TestConcludeAbTest:
    def _setup_decided_test(self, tmp_data_dir, campaign_id="conclude-camp"):
        """Create a campaign in DECIDED state ready for conclusion."""
        campaign_dir = tmp_data_dir / "campaigns" / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)

        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": campaign_id,
            "campaign_name": "Conclude Test",
            "brief": "Test brief",
            "channel": "email",
            "num_variants": 2,
            "created_at": "2026-04-01T10:00:00",
            "status": "active",
        }))
        (campaign_dir / "variants.json").write_text(json.dumps([
            {"variant_id": "v1", "channel": "email", "content": "A", "status": "draft"},
            {"variant_id": "v2", "channel": "email", "content": "B", "status": "draft"},
        ]))
        state = {
            "test_id": "conclude-test-1",
            "campaign_id": campaign_id,
            "state": "DECIDED",
            "hypothesis": "v2 beats v1 on open rate",
            "variable_tested": "subject_line",
            "variants": {
                "control": {"variant_id": "v1"},
                "treatment": {"variant_id": "v2"},
            },
            "decision_criteria": {"primary_metric": "open_rate"},
            "winner": "v2",
            "result": {
                "verdict": "winner_treatment",
                "winner_variant": "v2",
                "p_value": 0.002,
                "test_statistic": 3.1,
                "test_type": "two-proportion z-test",
                "control_mean": 0.20,
                "treatment_mean": 0.35,
                "effect_size": 0.15,
                "relative_lift": 75.0,
                "early_stopped": False,
                "decided_at": "2026-04-03T12:00:00",
            },
            "learning_saved": False,
            "state_history": [
                {"state": "DESIGNED", "entered_at": "2026-04-01T10:00:00"},
                {"state": "DECIDED", "entered_at": "2026-04-03T12:00:00"},
            ],
            "checks_performed": [],
        }
        (campaign_dir / "ab_test_state.json").write_text(json.dumps(state, indent=2))
        return campaign_id

    def test_concludes_and_transitions_to_completed(self, tmp_data_dir):
        campaign_id = self._setup_decided_test(tmp_data_dir)
        result = call_tool(conclude_ab_test, campaign_id)
        assert "COMPLETED" in result

        state = json.loads(
            (tmp_data_dir / "campaigns" / campaign_id / "ab_test_state.json").read_text()
        )
        assert state["state"] == "COMPLETED"

    def test_marks_winner_in_variants(self, tmp_data_dir):
        campaign_id = self._setup_decided_test(tmp_data_dir)
        call_tool(conclude_ab_test, campaign_id)

        variants = json.loads(
            (tmp_data_dir / "campaigns" / campaign_id / "variants.json").read_text()
        )
        winner = [v for v in variants if v["status"] == "winner"]
        loser = [v for v in variants if v["status"] == "loser"]
        assert len(winner) == 1
        assert winner[0]["variant_id"] == "v2"
        assert len(loser) == 1

    def test_produces_learning_recommendation(self, tmp_data_dir):
        campaign_id = self._setup_decided_test(tmp_data_dir)
        result = call_tool(conclude_ab_test, campaign_id)
        assert "learning" in result.lower() or "save_learning" in result.lower()

        state = json.loads(
            (tmp_data_dir / "campaigns" / campaign_id / "ab_test_state.json").read_text()
        )
        assert state["learning_saved"] is True
        assert "learning_recommendation" in state

    def test_wrong_state_returns_error(self, seed_ab_test, tmp_data_dir):
        """Concluding a COLLECTING test should fail."""
        campaign_id, _ = seed_ab_test
        result = call_tool(conclude_ab_test, campaign_id)
        assert "Error" in result

    def test_inconclusive_test_concludes(self, tmp_data_dir):
        campaign_id = "inconclusive-camp"
        campaign_dir = tmp_data_dir / "campaigns" / campaign_id
        campaign_dir.mkdir(parents=True)

        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": campaign_id, "channel": "email", "status": "active"
        }))
        (campaign_dir / "variants.json").write_text(json.dumps([
            {"variant_id": "v1", "status": "draft"},
            {"variant_id": "v2", "status": "draft"},
        ]))
        state = {
            "test_id": "inc-test",
            "campaign_id": campaign_id,
            "state": "INCONCLUSIVE",
            "hypothesis": "Test",
            "variable_tested": "tone",
            "variants": {
                "control": {"variant_id": "v1"},
                "treatment": {"variant_id": "v2"},
            },
            "decision_criteria": {"primary_metric": "click_rate"},
            "winner": None,
            "result": {
                "verdict": "inconclusive",
                "reason": "Max duration reached",
                "p_value": 0.25,
            },
            "learning_saved": False,
            "state_history": [],
            "checks_performed": [],
        }
        (campaign_dir / "ab_test_state.json").write_text(json.dumps(state, indent=2))

        result = call_tool(conclude_ab_test, campaign_id)
        assert "COMPLETED" in result
        assert "inconclusive" in result.lower()


# =========================================================================
# list_active_tests
# =========================================================================

class TestListActiveTests:
    def test_no_tests_returns_message(self, tmp_data_dir):
        result = call_tool(list_active_tests)
        assert "No active" in result

    def test_lists_collecting_test(self, seed_ab_test, tmp_data_dir):
        result = call_tool(list_active_tests)
        campaign_id, test_id = seed_ab_test
        assert test_id in result
        assert campaign_id in result
        assert "COLLECTING" in result

    def test_excludes_completed_tests(self, tmp_data_dir):
        """COMPLETED tests should not appear in active list."""
        campaign_dir = tmp_data_dir / "campaigns" / "done-camp"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "ab_test_state.json").write_text(json.dumps({
            "test_id": "done-test",
            "campaign_id": "done-camp",
            "state": "COMPLETED",
            "checks_performed": [],
        }))
        result = call_tool(list_active_tests)
        assert "done-test" not in result
