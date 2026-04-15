"""
Tests for tools/metrics_tools.py — metric logging and retrieval.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.metrics_tools import get_variant_metrics, log_metrics


class TestLogMetrics:
    def test_logs_metric_entry(self, seed_campaign, tmp_data_dir):
        result = call_tool(log_metrics, seed_campaign, "v1", "conversion_rate", 0.12, "2026-04-02")
        assert "conversion_rate" in result
        assert "0.12" in result

        metrics = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "metrics.json").read_text()
        )
        # seed_campaign already has 4 metrics, we added 1
        assert len(metrics) == 5
        new_entry = metrics[-1]
        assert new_entry["metric_type"] == "conversion_rate"
        assert new_entry["value"] == 0.12
        assert new_entry["variant_id"] == "v1"

    def test_nonexistent_campaign_returns_error(self, tmp_data_dir):
        result = call_tool(log_metrics, "fake-campaign", "v1", "open_rate", 0.5)
        assert "Error" in result
        assert "not found" in result

    def test_invalid_metric_type_returns_error(self, seed_campaign):
        result = call_tool(log_metrics, seed_campaign, "v1", "made_up_metric", 0.5)
        assert "Error" in result
        assert "Invalid metric_type" in result

    def test_defaults_date_to_today(self, seed_campaign, tmp_data_dir):
        call_tool(log_metrics, seed_campaign, "v1", "impressions", 1000)
        metrics = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "metrics.json").read_text()
        )
        last = metrics[-1]
        assert last["date"] != ""
        # Should be a valid YYYY-MM-DD format
        assert len(last["date"]) == 10

    def test_preserves_existing_metrics(self, seed_campaign, tmp_data_dir):
        """Logging a new metric should not overwrite existing ones."""
        metrics_before = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "metrics.json").read_text()
        )
        count_before = len(metrics_before)

        call_tool(log_metrics, seed_campaign, "v2", "roas", 3.5)

        metrics_after = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "metrics.json").read_text()
        )
        assert len(metrics_after) == count_before + 1

    def test_notes_field_stored(self, seed_campaign, tmp_data_dir):
        call_tool(log_metrics, seed_campaign, "v1", "clicks", 150, "2026-04-02", "From Google Ads")
        metrics = json.loads(
            (tmp_data_dir / "campaigns" / seed_campaign / "metrics.json").read_text()
        )
        last = metrics[-1]
        assert last["notes"] == "From Google Ads"


class TestGetVariantMetrics:
    def test_returns_all_variants_comparison(self, seed_campaign):
        result = call_tool(get_variant_metrics, seed_campaign)
        assert "v1" in result
        assert "v2" in result
        assert "open_rate" in result
        assert "click_rate" in result

    def test_filter_by_variant_id(self, seed_campaign):
        result = call_tool(get_variant_metrics, seed_campaign, "v1")
        assert "v1" in result
        assert "open_rate" in result
        # Should not contain v2's data in the header
        assert "Metrics for variant 'v1'" in result

    def test_nonexistent_campaign_returns_error(self, tmp_data_dir):
        result = call_tool(get_variant_metrics, "no-such-campaign")
        assert "Error" in result

    def test_no_metrics_message(self, tmp_data_dir):
        """Campaign with no metrics.json → appropriate message."""
        from tools.copy_tools import generate_copy
        call_tool(generate_copy, "Brief", "email", 1, "no-metrics")
        result = call_tool(get_variant_metrics, "no-metrics")
        assert "No metrics logged" in result

    def test_nonexistent_variant_returns_no_metrics(self, seed_campaign):
        result = call_tool(get_variant_metrics, seed_campaign, "v99")
        assert "No metrics found" in result
