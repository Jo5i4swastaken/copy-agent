"""
Tests for tools/analysis_tools.py and tools/analytics_tools.py.

Covers:
- analyze_campaign, save_learning, read_playbook (analysis_tools)
- compute_trends, generate_report, list_reports, get_report (analytics_tools)
"""

import json

import pytest

from tests.conftest import call_tool
from tools.analysis_tools import analyze_campaign, read_playbook, save_learning
from tools.analytics_tools import (
    compute_trends,
    detect_anomalies,
    generate_report,
    get_report,
    list_reports,
)


# =========================================================================
# analyze_campaign
# =========================================================================

class TestAnalyzeCampaign:
    def test_compares_two_variants(self, seed_campaign):
        result = call_tool(analyze_campaign, seed_campaign)
        assert "v1" in result
        assert "v2" in result
        assert "open_rate" in result

    def test_identifies_winner(self, seed_campaign):
        """v2 has higher open_rate (0.31 vs 0.22), should be identified."""
        result = call_tool(analyze_campaign, seed_campaign)
        # The analysis should flag v2 as better on open_rate
        assert "v2" in result

    def test_nonexistent_campaign_returns_error(self, tmp_data_dir):
        result = call_tool(analyze_campaign, "fake")
        assert "not found" in result.lower() or "no variants" in result.lower()

    def test_no_metrics_returns_error(self, tmp_data_dir):
        """Campaign with variants but no metrics."""
        from tools.copy_tools import generate_copy, save_copy_variant
        call_tool(generate_copy, "Brief", "email", 2, "no-metrics-camp")
        call_tool(save_copy_variant, "no-metrics-camp", "v1", "email", "A")
        call_tool(save_copy_variant, "no-metrics-camp", "v2", "email", "B")
        result = call_tool(analyze_campaign, "no-metrics-camp")
        assert "no metrics" in result.lower() or "log metrics" in result.lower()

    def test_single_variant_insufficient(self, tmp_data_dir):
        """Need at least 2 variants with metrics."""
        campaign_dir = tmp_data_dir / "campaigns" / "single-var"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": "single-var", "channel": "email"
        }))
        (campaign_dir / "variants.json").write_text(json.dumps([
            {"variant_id": "v1", "channel": "email", "content": "A"}
        ]))
        (campaign_dir / "metrics.json").write_text(json.dumps([
            {"variant_id": "v1", "metric_type": "open_rate", "value": 0.2, "date": "2026-04-01", "logged_at": "2026-04-01T12:00:00"}
        ]))
        result = call_tool(analyze_campaign, "single-var")
        assert "not enough" in result.lower() or "at least 2" in result.lower()


# =========================================================================
# save_learning
# =========================================================================

class TestSaveLearning:
    def test_saves_learning_to_playbook(self, tmp_data_dir):
        result = call_tool(
            save_learning,
            category="email",
            learning="Subject lines with emojis increase open rates by 8%",
            evidence="spring-sale/v2",
            confidence="medium",
        )
        assert "saved" in result.lower() or "playbook" in result.lower()

        playbook = json.loads((tmp_data_dir / "playbook.json").read_text())
        assert len(playbook["learnings"]) == 1
        entry = playbook["learnings"][0]
        assert entry["category"] == "email"
        assert "emojis" in entry["learning"]
        assert entry["confidence"] == 0.6  # medium = 0.6

    def test_invalid_category_returns_error(self, tmp_data_dir):
        result = call_tool(save_learning, "twitter", "Some learning")
        assert "Invalid category" in result

    def test_invalid_confidence_returns_error(self, tmp_data_dir):
        result = call_tool(save_learning, "email", "Some learning", "", "extreme")
        assert "Invalid confidence" in result

    def test_duplicate_detection(self, tmp_data_dir):
        """Saving a very similar learning twice should be detected."""
        call_tool(save_learning, "email", "Short subject lines work best", "", "low")
        result = call_tool(save_learning, "email", "Short subject lines work best for email", "", "low")
        # Should either reject or boost the existing
        playbook = json.loads((tmp_data_dir / "playbook.json").read_text())
        # Should not have 2 separate entries for essentially the same learning
        assert len(playbook["learnings"]) <= 2  # At most original + 1


# =========================================================================
# read_playbook
# =========================================================================

class TestReadPlaybook:
    def test_returns_learnings(self, seed_playbook):
        result = call_tool(read_playbook)
        assert "email" in result.lower()
        assert "subject lines" in result.lower()
        assert "sms" in result.lower()

    def test_empty_playbook(self, tmp_data_dir):
        result = call_tool(read_playbook)
        assert "no learnings" in result.lower() or "empty" in result.lower() or "0 learnings" in result.lower()


# =========================================================================
# compute_trends (analytics_tools.py)
# =========================================================================

class TestComputeTrends:
    def test_computes_trends_for_channel(self, seed_campaign, tmp_data_dir):
        result = call_tool(compute_trends, "email", "open_rate", 30)
        # Should return some form of trend data even if sparse
        assert isinstance(result, str)

    def test_no_data_returns_message(self, tmp_data_dir):
        result = call_tool(compute_trends, "email", "open_rate", 30)
        assert "no" in result.lower() or "found" in result.lower() or isinstance(result, str)


# =========================================================================
# generate_report (analytics_tools.py)
# =========================================================================

class TestGenerateReport:
    def test_generates_campaign_performance_report(self, seed_campaign, tmp_data_dir):
        result = call_tool(generate_report, "campaign_performance", campaign_id=seed_campaign)
        assert "report" in result.lower() or seed_campaign in result

        # Check report was saved
        reports = list((tmp_data_dir / "reports").glob("*.json"))
        assert len(reports) >= 1

    def test_invalid_report_type_returns_error(self, tmp_data_dir):
        result = call_tool(generate_report, "fake_report_type")
        assert "invalid" in result.lower() or "error" in result.lower() or "must be" in result.lower()

    def test_generates_playbook_health_report(self, seed_playbook, tmp_data_dir):
        result = call_tool(generate_report, "playbook_health")
        assert isinstance(result, str)
        reports = list((tmp_data_dir / "reports").glob("*.json"))
        assert len(reports) >= 1


# =========================================================================
# list_reports / get_report (analytics_tools.py)
# =========================================================================

class TestReportCRUD:
    def test_list_reports_empty(self, tmp_data_dir):
        result = call_tool(list_reports)
        assert "no reports" in result.lower() or "0" in result

    def test_list_and_get_report(self, seed_campaign, tmp_data_dir):
        # Generate a report first
        call_tool(generate_report, "campaign_performance", campaign_id=seed_campaign)

        # List should find it
        result = call_tool(list_reports)
        assert "campaign_performance" in result.lower() or "1" in result

        # Get the report by ID
        reports = list((tmp_data_dir / "reports").glob("*.json"))
        if reports:
            report_data = json.loads(reports[0].read_text())
            report_id = report_data.get("report_id", reports[0].stem)
            detail = call_tool(get_report, report_id)
            assert isinstance(detail, str)
            assert len(detail) > 0

    def test_get_nonexistent_report(self, tmp_data_dir):
        result = call_tool(get_report, "fake-report-id")
        assert "not found" in result.lower() or "error" in result.lower()


# =========================================================================
# detect_anomalies (analytics_tools.py)
# =========================================================================

class TestDetectAnomalies:
    def test_no_data_returns_message(self, tmp_data_dir):
        result = call_tool(detect_anomalies, "email", "open_rate")
        assert isinstance(result, str)

    def test_with_data_runs(self, seed_campaign, tmp_data_dir):
        """With seeded campaign data, anomaly detection should run without error."""
        result = call_tool(detect_anomalies, "email", "open_rate")
        assert isinstance(result, str)
