"""
Tests for context.py — context factory helper functions.

Tests the individual builder functions directly since the @context_factory
decorator is framework-specific. Monkeypatches the module-level path
variables in context.py.
"""

import json

import pytest

import context as ctx


@pytest.fixture(autouse=True)
def patch_context_paths(tmp_path, monkeypatch):
    """Monkeypatch all path variables in context.py to point to tmp_path."""
    data_dir = tmp_path / "data"
    campaigns_dir = data_dir / "campaigns"
    campaigns_dir.mkdir(parents=True)
    (data_dir / "orchestration" / "transfers").mkdir(parents=True)
    (data_dir / "reports").mkdir(parents=True)

    # Empty playbook
    (data_dir / "playbook.json").write_text(
        json.dumps({"learnings": []}), encoding="utf-8"
    )

    monkeypatch.setattr(ctx, "_DATA_DIR", data_dir)
    monkeypatch.setattr(ctx, "_PLAYBOOK_PATH", data_dir / "playbook.json")
    monkeypatch.setattr(ctx, "_CAMPAIGNS_DIR", campaigns_dir)
    monkeypatch.setattr(ctx, "_ORCHESTRATION_DIR", data_dir / "orchestration")
    monkeypatch.setattr(ctx, "_REPORTS_DIR", data_dir / "reports")

    return data_dir


# =========================================================================
# _build_playbook_summary
# =========================================================================

class TestBuildPlaybookSummary:
    def test_empty_playbook(self, patch_context_paths):
        result = ctx._build_playbook_summary()
        assert "no playbook" in result.lower() or "generate campaigns" in result.lower()

    def test_with_learnings(self, patch_context_paths):
        playbook = {
            "version": 2,
            "learnings": [
                {
                    "category": "email",
                    "learning": "Short subject lines get higher open rates",
                    "confidence": 0.8,
                    "times_confirmed": 3,
                },
                {
                    "category": "sms",
                    "learning": "Action verbs boost CTR",
                    "confidence": 0.6,
                    "times_confirmed": 1,
                },
            ],
        }
        (patch_context_paths / "playbook.json").write_text(json.dumps(playbook))
        result = ctx._build_playbook_summary()
        assert "Email" in result
        assert "Sms" in result
        assert "Short subject lines" in result
        assert "Action verbs" in result
        assert "v2" in result

    def test_filters_low_confidence(self, patch_context_paths):
        playbook = {
            "version": 1,
            "learnings": [
                {"category": "email", "learning": "High conf", "confidence": 0.9},
                {"category": "email", "learning": "Too low", "confidence": 0.1},
            ],
        }
        (patch_context_paths / "playbook.json").write_text(json.dumps(playbook))
        result = ctx._build_playbook_summary()
        assert "High conf" in result
        assert "Too low" not in result

    def test_truncates_to_max(self, patch_context_paths):
        learnings = [
            {"category": "email", "learning": f"Learning {i}", "confidence": 0.5}
            for i in range(30)
        ]
        (patch_context_paths / "playbook.json").write_text(
            json.dumps({"version": 1, "learnings": learnings})
        )
        result = ctx._build_playbook_summary()
        # Should only show top _MAX_LEARNINGS (20)
        assert "Learning 0" in result
        assert result.count("- [") <= 20


# =========================================================================
# _build_recent_performance
# =========================================================================

class TestBuildRecentPerformance:
    def test_no_campaigns(self, patch_context_paths):
        result = ctx._build_recent_performance()
        assert "no campaigns" in result.lower()

    def test_with_campaigns(self, patch_context_paths):
        campaign_dir = patch_context_paths / "campaigns" / "test-camp"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": "test-camp",
            "channel": "email",
            "status": "active",
            "created_at": "2026-04-01T10:00:00",
        }))
        (campaign_dir / "variants.json").write_text(json.dumps([
            {"variant_id": "v1"}, {"variant_id": "v2"},
        ]))

        result = ctx._build_recent_performance()
        assert "test-camp" in result
        assert "email" in result
        assert "2 variant" in result


# =========================================================================
# _build_active_ab_tests_summary
# =========================================================================

class TestBuildActiveAbTestsSummary:
    def test_no_tests_returns_empty(self, patch_context_paths):
        result = ctx._build_active_ab_tests_summary()
        assert result == ""

    def test_with_collecting_test(self, patch_context_paths):
        campaign_dir = patch_context_paths / "campaigns" / "ab-camp"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "ab_test_state.json").write_text(json.dumps({
            "test_id": "test-123",
            "campaign_id": "ab-camp",
            "state": "COLLECTING",
            "hypothesis": "V2 is better",
            "next_check_at": "2026-04-05T12:00:00",
        }))

        result = ctx._build_active_ab_tests_summary()
        assert "test-123" in result
        assert "COLLECTING" in result
        assert "V2 is better" in result

    def test_excludes_completed(self, patch_context_paths):
        campaign_dir = patch_context_paths / "campaigns" / "done-camp"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "ab_test_state.json").write_text(json.dumps({
            "test_id": "done-test",
            "state": "COMPLETED",
        }))

        result = ctx._build_active_ab_tests_summary()
        assert result == ""


# =========================================================================
# _build_pending_transfers_summary
# =========================================================================

class TestBuildPendingTransfersSummary:
    def test_no_transfers_returns_empty(self, patch_context_paths):
        result = ctx._build_pending_transfers_summary()
        assert result == ""

    def test_with_proposed_transfer(self, patch_context_paths):
        tf = {
            "transfer_id": "tf-001",
            "source_channel": "email",
            "target_channel": "sms",
            "hypothesis": "Playful tone works for SMS",
            "status": "proposed",
        }
        (patch_context_paths / "orchestration" / "transfers" / "tf-001.json").write_text(
            json.dumps(tf)
        )

        result = ctx._build_pending_transfers_summary()
        assert "tf-001" in result
        assert "email" in result
        assert "sms" in result
        assert "proposed" in result

    def test_excludes_confirmed(self, patch_context_paths):
        tf = {
            "transfer_id": "tf-done",
            "source_channel": "email",
            "target_channel": "sms",
            "status": "confirmed",
        }
        (patch_context_paths / "orchestration" / "transfers" / "tf-done.json").write_text(
            json.dumps(tf)
        )

        result = ctx._build_pending_transfers_summary()
        assert result == ""


# =========================================================================
# _build_recent_anomalies
# =========================================================================

class TestBuildRecentAnomalies:
    def test_no_reports_returns_empty(self, patch_context_paths):
        result = ctx._build_recent_anomalies()
        assert result == ""

    def test_with_anomaly_report(self, patch_context_paths):
        report = {
            "report_type": "anomaly_alerts",
            "anomalies": [
                {"channel": "email", "metric": "open_rate", "direction": "spike", "z_score": 3.2},
                {"channel": "sms", "metric": "click_rate", "direction": "drop", "z_score": -2.5},
            ],
        }
        (patch_context_paths / "reports" / "report-anom.json").write_text(
            json.dumps(report)
        )

        result = ctx._build_recent_anomalies()
        assert "email" in result
        assert "spike" in result
        assert "3.2" in result

    def test_ignores_non_anomaly_reports(self, patch_context_paths):
        report = {
            "report_type": "campaign_performance",
            "content": {"some": "data"},
        }
        (patch_context_paths / "reports" / "report-perf.json").write_text(
            json.dumps(report)
        )

        result = ctx._build_recent_anomalies()
        assert result == ""
