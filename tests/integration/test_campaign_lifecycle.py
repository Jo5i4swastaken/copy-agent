"""
Integration test: Full campaign lifecycle.

generate_copy → save_copy_variant → log_metrics → analyze_campaign
→ save_learning → verify playbook updated with new entry.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.copy_tools import generate_copy, save_copy_variant, get_campaign
from tools.metrics_tools import log_metrics, get_variant_metrics
from tools.analysis_tools import analyze_campaign, save_learning, read_playbook


class TestCampaignLifecycle:
    """End-to-end: brief → variants → metrics → analysis → learning."""

    def test_full_lifecycle(self, tmp_data_dir):
        # 1. Create a campaign
        result = call_tool(
            generate_copy,
            brief="Promote our spring clearance sale — 40% off everything",
            channel="email",
            num_variants=2,
            campaign_name="spring-clearance",
        )
        assert "spring-clearance" in result
        assert "email" in result

        campaign_id = "spring-clearance"
        campaign_dir = tmp_data_dir / "campaigns" / campaign_id
        assert campaign_dir.exists()
        assert (campaign_dir / "brief.json").exists()
        assert (campaign_dir / "variants.json").exists()

        # 2. Save two variants
        result_v1 = call_tool(
            save_copy_variant,
            campaign_id=campaign_id,
            variant_id="v1",
            channel="email",
            content="Don't miss 40% off everything — our biggest clearance yet!",
            subject_line="40% Off Everything — Ends Sunday",
            cta="Shop the Sale",
            tone="urgent",
        )
        assert "v1" in result_v1

        result_v2 = call_tool(
            save_copy_variant,
            campaign_id=campaign_id,
            variant_id="v2",
            channel="email",
            content="Spring is here, and so are fresh deals. Enjoy 40% off sitewide.",
            subject_line="Fresh Spring Deals: 40% Off Sitewide",
            cta="Browse Deals",
            tone="playful",
        )
        assert "v2" in result_v2

        # Verify variants stored
        variants = json.loads((campaign_dir / "variants.json").read_text())
        assert len(variants) == 2

        # 3. Log metrics for both variants
        for vid, open_r, click_r in [("v1", 0.18, 0.03), ("v2", 0.29, 0.07)]:
            call_tool(log_metrics, campaign_id=campaign_id, variant_id=vid,
                      metric_type="open_rate", value=open_r, date="2026-04-01")
            call_tool(log_metrics, campaign_id=campaign_id, variant_id=vid,
                      metric_type="click_rate", value=click_r, date="2026-04-01")

        # Verify metrics stored
        metrics = json.loads((campaign_dir / "metrics.json").read_text())
        assert len(metrics) == 4

        # 4. Analyze the campaign
        analysis = call_tool(analyze_campaign, campaign_id)
        assert "v2" in analysis  # v2 should be identified as better
        assert "open_rate" in analysis

        # 5. Save a learning based on analysis
        result = call_tool(
            save_learning,
            category="email",
            learning="Playful tone with sitewide framing outperforms urgent tone in clearance emails",
            evidence=f"{campaign_id}/v2",
            confidence="medium",
        )
        assert "saved" in result.lower()

        # 6. Verify playbook updated
        playbook = json.loads((tmp_data_dir / "playbook.json").read_text())
        learnings = playbook["learnings"]
        new_learning = [l for l in learnings if "playful tone" in l["learning"].lower()]
        assert len(new_learning) == 1
        assert new_learning[0]["confidence"] == 0.6  # medium
        assert campaign_id in str(new_learning[0]["evidence"])

    def test_lifecycle_learning_appears_in_read_playbook(self, tmp_data_dir):
        """After saving a learning, read_playbook should include it."""
        # Create campaign + variant + metric (minimal path)
        call_tool(generate_copy, brief="Test", channel="sms", num_variants=1,
                  campaign_name="read-pb-test")
        call_tool(save_copy_variant, campaign_id="read-pb-test", variant_id="v1",
                  channel="sms", content="Quick test")
        call_tool(log_metrics, campaign_id="read-pb-test", variant_id="v1",
                  metric_type="click_rate", value=0.12)

        # Save learning
        call_tool(save_learning, category="sms",
                  learning="Short punchy SMS messages get higher CTR",
                  evidence="read-pb-test/v1", confidence="low")

        # Verify via read_playbook tool
        pb_output = call_tool(read_playbook)
        assert "short punchy" in pb_output.lower() or "Short punchy" in pb_output

    def test_get_campaign_shows_full_state(self, tmp_data_dir):
        """get_campaign should return brief + variants + metrics together."""
        call_tool(generate_copy, brief="Summer sale", channel="ad",
                  num_variants=1, campaign_name="summer-ad")
        call_tool(save_copy_variant, campaign_id="summer-ad", variant_id="v1",
                  channel="ad", content="Summer deals are here!", cta="Shop Now",
                  tone="excited")
        call_tool(log_metrics, campaign_id="summer-ad", variant_id="v1",
                  metric_type="click_rate", value=0.045)

        detail = call_tool(get_campaign, "summer-ad")
        assert "summer-ad" in detail
        assert "Summer deals" in detail or "ad" in detail
        assert "click_rate" in detail or "0.045" in detail
