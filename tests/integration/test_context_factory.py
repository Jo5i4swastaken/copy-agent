"""
Integration test: Context factory with real seeded data.

Seeds campaigns, A/B tests, transfers, and anomaly reports via the tool
chain, then calls context.py helpers to verify all template variables
are populated correctly.
"""

import json

import pytest

import context as ctx
from tests.conftest import call_tool
from tools.copy_tools import generate_copy, save_copy_variant
from tools.metrics_tools import log_metrics
from tools.analysis_tools import save_learning
from tools.orchestration_tools import plan_multi_channel_campaign
from tools.cross_channel_tools import evaluate_cross_channel_transfer


@pytest.fixture(autouse=True)
def patch_context_paths(tmp_path, monkeypatch):
    """Redirect context.py paths to a tmp directory matching conftest layout."""
    data_dir = tmp_path / "data"
    campaigns_dir = data_dir / "campaigns"
    campaigns_dir.mkdir(parents=True)
    (data_dir / "orchestration" / "transfers").mkdir(parents=True)
    (data_dir / "orchestration" / "manifests").mkdir(parents=True)
    (data_dir / "reports").mkdir(parents=True)

    # Seed empty playbook
    (data_dir / "playbook.json").write_text(
        json.dumps({"learnings": []}), encoding="utf-8"
    )

    # Patch context.py module-level paths
    monkeypatch.setattr(ctx, "_DATA_DIR", data_dir)
    monkeypatch.setattr(ctx, "_PLAYBOOK_PATH", data_dir / "playbook.json")
    monkeypatch.setattr(ctx, "_CAMPAIGNS_DIR", campaigns_dir)
    monkeypatch.setattr(ctx, "_ORCHESTRATION_DIR", data_dir / "orchestration")
    monkeypatch.setattr(ctx, "_REPORTS_DIR", data_dir / "reports")

    # Also patch all tool modules so they write to the same tmp dirs
    from tests.conftest import _TOOL_MODULES_WITH_DATA_DIR, _MODULES_WITH_CAMPAIGNS_DIR
    for mod_name in _TOOL_MODULES_WITH_DATA_DIR:
        try:
            mod = __import__(mod_name, fromlist=["DATA_DIR"])
            monkeypatch.setattr(mod, "DATA_DIR", data_dir)
        except (ImportError, AttributeError):
            pass
    for mod_name in _MODULES_WITH_CAMPAIGNS_DIR:
        try:
            mod = __import__(mod_name, fromlist=["CAMPAIGNS_DIR"])
            monkeypatch.setattr(mod, "CAMPAIGNS_DIR", campaigns_dir)
        except (ImportError, AttributeError):
            pass

    # analytics_tools extras
    try:
        import tools.analytics_tools as at
        monkeypatch.setattr(at, "PLAYBOOK_PATH", data_dir / "playbook.json")
        monkeypatch.setattr(at, "REPORTS_DIR", data_dir / "reports")
    except (ImportError, AttributeError):
        pass

    # orchestration_tools
    try:
        import tools.orchestration_tools as ot
        monkeypatch.setattr(ot, "ORCHESTRATION_DIR", data_dir / "orchestration")
    except (ImportError, AttributeError):
        pass

    # cross_channel_tools
    try:
        import tools.cross_channel_tools as cct
        monkeypatch.setattr(cct, "PLAYBOOK_PATH", data_dir / "playbook.json")
        monkeypatch.setattr(cct, "TRANSFERS_DIR", data_dir / "orchestration" / "transfers")
    except (ImportError, AttributeError):
        pass

    return data_dir


class TestContextFactoryIntegration:
    def test_playbook_summary_after_saving_learnings(self, patch_context_paths):
        """After saving real learnings, playbook_summary should include them."""
        call_tool(save_learning, category="email",
                  learning="Subject lines with numbers get 20% higher open rates",
                  evidence="test/v1", confidence="high")
        call_tool(save_learning, category="sms",
                  learning="Action verbs boost CTR by 10%",
                  evidence="sms-test/v1", confidence="medium")

        summary = ctx._build_playbook_summary()
        assert "numbers" in summary.lower() or "Subject lines" in summary
        assert "action verbs" in summary.lower() or "Action verbs" in summary
        assert "Email" in summary
        assert "Sms" in summary

    def test_recent_performance_after_creating_campaigns(self, patch_context_paths):
        """After creating campaigns with variants, recent_performance shows them."""
        call_tool(generate_copy, brief="Spring sale email", channel="email",
                  num_variants=2, campaign_name="ctx-spring-email")
        call_tool(save_copy_variant, campaign_id="ctx-spring-email",
                  variant_id="v1", channel="email", content="Spring deals!")
        call_tool(save_copy_variant, campaign_id="ctx-spring-email",
                  variant_id="v2", channel="email", content="Fresh spring savings")

        perf = ctx._build_recent_performance()
        assert "ctx-spring-email" in perf
        assert "email" in perf
        assert "2 variant" in perf

    def test_active_ab_tests_after_starting_test(self, patch_context_paths):
        """After starting an A/B test, context shows it as active."""
        call_tool(generate_copy, brief="AB test campaign", channel="email",
                  num_variants=2, campaign_name="ctx-ab-camp")

        # Write AB test state directly (faster than full design+start flow)
        campaign_dir = patch_context_paths / "campaigns" / "ctx-ab-camp"
        (campaign_dir / "ab_test_state.json").write_text(json.dumps({
            "test_id": "ctx-test-001",
            "campaign_id": "ctx-ab-camp",
            "state": "COLLECTING",
            "hypothesis": "Playful tone beats professional",
            "next_check_at": "2026-04-05T12:00:00",
        }))

        result = ctx._build_active_ab_tests_summary()
        assert "ctx-test-001" in result
        assert "COLLECTING" in result
        assert "Playful tone" in result

    def test_pending_transfers_after_evaluate(self, patch_context_paths):
        """After evaluating a learning for transfer, context shows pending transfers."""
        # Seed a transferable learning
        playbook = {
            "learnings": [{
                "id": "learn_ctx_001",
                "category": "email",
                "subcategory": "tone",
                "learning": "Playful tone boosts engagement",
                "confidence": 0.7,
                "times_confirmed": 3,
            }]
        }
        (patch_context_paths / "playbook.json").write_text(
            json.dumps(playbook, indent=2), encoding="utf-8"
        )

        call_tool(evaluate_cross_channel_transfer, "learn_ctx_001")

        result = ctx._build_pending_transfers_summary()
        assert "proposed" in result.lower()
        assert "email" in result

    def test_anomalies_with_seeded_report(self, patch_context_paths):
        """After writing an anomaly report, _build_recent_anomalies includes it."""
        report = {
            "report_type": "anomaly_alerts",
            "anomalies": [
                {"channel": "email", "metric": "open_rate",
                 "direction": "spike", "z_score": 3.5},
            ],
        }
        (patch_context_paths / "reports" / "report-anom-001.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

        result = ctx._build_recent_anomalies()
        assert "email" in result
        assert "spike" in result

    def test_all_sections_populated(self, patch_context_paths):
        """After seeding everything, all context sections should be non-empty."""
        # Playbook
        call_tool(save_learning, category="email",
                  learning="Test learning for context",
                  evidence="test/v1", confidence="medium")

        # Campaign
        call_tool(generate_copy, brief="Full test", channel="email",
                  num_variants=1, campaign_name="ctx-full-camp")
        call_tool(save_copy_variant, campaign_id="ctx-full-camp",
                  variant_id="v1", channel="email", content="Copy text")

        # AB test
        camp_dir = patch_context_paths / "campaigns" / "ctx-full-camp"
        (camp_dir / "ab_test_state.json").write_text(json.dumps({
            "test_id": "ctx-full-test",
            "campaign_id": "ctx-full-camp",
            "state": "COLLECTING",
            "hypothesis": "Test hypothesis",
            "next_check_at": "2026-04-10T12:00:00",
        }))

        # Transfer
        (patch_context_paths / "orchestration" / "transfers" / "transfer-ctx-001.json").write_text(
            json.dumps({
                "transfer_id": "transfer-ctx-001",
                "source_channel": "email",
                "target_channel": "sms",
                "hypothesis": "Test transfer",
                "status": "proposed",
            })
        )

        # Anomaly report
        (patch_context_paths / "reports" / "report-anom-full.json").write_text(
            json.dumps({
                "report_type": "anomaly_alerts",
                "anomalies": [{"channel": "sms", "metric": "click_rate",
                               "direction": "drop", "z_score": -2.8}],
            })
        )

        # Now check all sections
        playbook = ctx._build_playbook_summary()
        assert "learning" in playbook.lower()

        perf = ctx._build_recent_performance()
        assert "ctx-full-camp" in perf

        ab = ctx._build_active_ab_tests_summary()
        assert "ctx-full-test" in ab

        transfers = ctx._build_pending_transfers_summary()
        assert "transfer-ctx-001" in transfers

        anomalies = ctx._build_recent_anomalies()
        assert "sms" in anomalies
