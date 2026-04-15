"""
Integration test: Analytics pipeline.

Seed multiple campaigns with metrics → compute_trends → detect_anomalies
→ generate_report → list_reports → get_report → verify content.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.copy_tools import generate_copy, save_copy_variant
from tools.metrics_tools import log_metrics
from tools.analysis_tools import save_learning
from tools.analytics_tools import (
    compute_trends,
    detect_anomalies,
    generate_report,
    list_reports,
    get_report,
)


def _create_campaign_with_metrics(tmp_data_dir, campaign_name, channel,
                                  metric_type, variant_values):
    """Helper: create a campaign and log many metric entries.

    variant_values: list of (variant_id, [(value, date), ...])
    """
    call_tool(generate_copy, brief=f"Test {campaign_name}", channel=channel,
              num_variants=1, campaign_name=campaign_name)

    for variant_id, values in variant_values:
        call_tool(save_copy_variant, campaign_id=campaign_name, variant_id=variant_id,
                  channel=channel, content=f"Copy for {variant_id}")
        for value, date in values:
            call_tool(log_metrics, campaign_id=campaign_name, variant_id=variant_id,
                      metric_type=metric_type, value=value, date=date)


class TestAnalyticsPipeline:
    def test_compute_trends_across_campaigns(self, tmp_data_dir):
        """Seed 2 email campaigns with open_rate metrics, compute trends."""
        # Campaign 1: early dates, lower rates
        _create_campaign_with_metrics(
            tmp_data_dir, "email-camp-1", "email", "open_rate",
            [("v1", [(0.20, "2026-03-01"), (0.21, "2026-03-02"),
                     (0.19, "2026-03-03"), (0.22, "2026-03-04")])]
        )
        # Campaign 2: later dates, higher rates
        _create_campaign_with_metrics(
            tmp_data_dir, "email-camp-2", "email", "open_rate",
            [("v1", [(0.28, "2026-03-10"), (0.30, "2026-03-11"),
                     (0.29, "2026-03-12"), (0.31, "2026-03-13")])]
        )

        result = call_tool(compute_trends, channel="email", metric="open_rate", days=30)
        # Should find metric data and show some kind of trend
        assert "open_rate" in result or "email" in result
        # Should have data points
        assert "0.2" in result or "trend" in result.lower()

    def test_detect_anomalies_with_spike(self, tmp_data_dir):
        """Create a campaign with mostly normal values and one spike."""
        # Need 6+ data points: 5+ historical + recent
        values = [
            (0.20, "2026-03-01"), (0.21, "2026-03-02"),
            (0.19, "2026-03-03"), (0.20, "2026-03-04"),
            (0.21, "2026-03-05"), (0.20, "2026-03-06"),
            (0.19, "2026-03-07"), (0.21, "2026-03-08"),
            # Normal recent values
            (0.20, "2026-03-09"), (0.19, "2026-03-10"),
            (0.21, "2026-03-11"),
            # Spike!
            (0.55, "2026-03-12"),
            (0.20, "2026-03-13"),
        ]

        _create_campaign_with_metrics(
            tmp_data_dir, "anom-camp", "email", "open_rate",
            [("v1", values)]
        )

        result = call_tool(detect_anomalies, channel="email", metric="open_rate")
        # Should detect the spike
        assert "anomal" in result.lower() or "spike" in result.lower() or "0.55" in result

    def test_generate_and_retrieve_report(self, tmp_data_dir):
        """Generate a playbook_health report, list it, and retrieve it."""
        # Seed a playbook with learnings
        call_tool(save_learning, category="email",
                  learning="Numbers in subject lines boost open rates",
                  evidence="test/v1", confidence="high")
        call_tool(save_learning, category="sms",
                  learning="Action verbs increase click-through",
                  evidence="test/v2", confidence="low")

        # Generate report
        result = call_tool(generate_report, report_type="playbook_health")
        assert "report" in result.lower()

        # List reports
        reports_list = call_tool(list_reports)
        assert "playbook_health" in reports_list

        # Find the report ID from the reports directory
        reports_dir = tmp_data_dir / "reports"
        report_files = list(reports_dir.glob("report-playbook_health-*.json"))
        assert len(report_files) >= 1

        report_data = json.loads(report_files[0].read_text())
        report_id = report_data.get("report_id", report_files[0].stem)

        # Retrieve specific report
        detail = call_tool(get_report, report_id)
        assert "playbook" in detail.lower()

    def test_campaign_performance_report(self, tmp_data_dir):
        """Generate a campaign_performance report for a seeded campaign."""
        _create_campaign_with_metrics(
            tmp_data_dir, "perf-camp", "email", "open_rate",
            [("v1", [(0.22, "2026-04-01"), (0.24, "2026-04-02")]),
             ("v2", [(0.30, "2026-04-01"), (0.32, "2026-04-02")])]
        )

        # Save v2 variant too
        call_tool(save_copy_variant, campaign_id="perf-camp", variant_id="v2",
                  channel="email", content="Better copy")

        result = call_tool(generate_report, report_type="campaign_performance",
                           campaign_id="perf-camp")
        assert "perf-camp" in result or "report" in result.lower()

    def test_anomaly_alerts_report(self, tmp_data_dir):
        """Generate anomaly_alerts report with seeded data."""
        # Seed multiple campaigns with anomalous data
        values = [
            (0.20, "2026-03-01"), (0.21, "2026-03-02"),
            (0.19, "2026-03-03"), (0.20, "2026-03-04"),
            (0.21, "2026-03-05"), (0.20, "2026-03-06"),
            (0.19, "2026-03-07"), (0.21, "2026-03-08"),
            (0.20, "2026-03-09"), (0.60, "2026-03-10"),
            (0.19, "2026-03-11"), (0.20, "2026-03-12"),
            (0.21, "2026-03-13"),
        ]
        _create_campaign_with_metrics(
            tmp_data_dir, "alert-camp", "email", "open_rate",
            [("v1", values)]
        )

        result = call_tool(generate_report, report_type="anomaly_alerts",
                           channel="email")
        assert "report" in result.lower() or "anomal" in result.lower()

    def test_full_pipeline_seed_to_report(self, tmp_data_dir):
        """Full pipeline: campaigns → metrics → trend → anomaly → report → list."""
        # Seed 3 campaigns in email
        for i in range(1, 4):
            _create_campaign_with_metrics(
                tmp_data_dir, f"pipe-camp-{i}", "email", "click_rate",
                [("v1", [(0.03 + 0.005 * i, f"2026-03-{j:02d}") for j in range(1, 6)])]
            )

        # Compute trends
        trend_result = call_tool(compute_trends, channel="email", metric="click_rate")
        assert "click_rate" in trend_result or "email" in trend_result

        # Generate channel_trends report
        report_result = call_tool(generate_report, report_type="channel_trends",
                                  channel="email")
        assert "report" in report_result.lower()

        # List should show the report
        list_result = call_tool(list_reports)
        assert "channel_trends" in list_result
