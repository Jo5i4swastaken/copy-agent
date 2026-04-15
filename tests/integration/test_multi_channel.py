"""
Integration test: Multi-channel campaign planning.

plan_multi_channel_campaign → verify per-channel campaign dirs + manifest
→ save variants per channel → log metrics → analyze.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.orchestration_tools import plan_multi_channel_campaign
from tools.copy_tools import save_copy_variant
from tools.metrics_tools import log_metrics
from tools.analysis_tools import analyze_campaign


class TestMultiChannelCampaign:
    def test_plan_and_populate_all_channels(self, tmp_data_dir):
        """Plan a 3-channel campaign, add variants + metrics, analyze each."""
        # 1. Plan campaign
        result = call_tool(
            plan_multi_channel_campaign,
            name="summer-promo",
            brief="Promote our summer clearance across all channels",
            channels="email,sms,ad",
            audience="Young professionals 25-35",
            constraints="No slang, brand-safe",
        )
        assert "summer-promo" in result
        assert "3" in result

        # 2. Verify per-channel campaign dirs and manifest
        for channel in ["email", "sms", "ad"]:
            campaign_id = f"summer-promo-{channel}"
            campaign_dir = tmp_data_dir / "campaigns" / campaign_id
            assert campaign_dir.exists()

            brief = json.loads((campaign_dir / "brief.json").read_text())
            assert brief["channel"] == channel
            assert brief["multi_channel_group"] == "summer-promo"
            assert brief["audience"] == "Young professionals 25-35"
            assert brief["constraints"] == "No slang, brand-safe"

        manifest_path = tmp_data_dir / "orchestration" / "manifests" / "summer-promo.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert set(manifest["channels"]) == {"email", "sms", "ad"}
        assert len(manifest["campaign_ids"]) == 3

        # 3. Add variants per channel
        channel_variants = {
            "email": ("Summer Clearance — 50% Off!", "Don't miss our biggest summer sale."),
            "sms": ("50% OFF today only! Shop now: link.co/summer", "Flash sale!"),
            "ad": ("Summer Sale 50% Off", "The biggest deals of the season."),
        }

        for channel, (content, cta) in channel_variants.items():
            campaign_id = f"summer-promo-{channel}"
            call_tool(
                save_copy_variant,
                campaign_id=campaign_id,
                variant_id="v1",
                channel=channel,
                content=content,
                cta=cta,
                tone="excited",
            )

        # 4. Log metrics per channel
        metrics_data = {
            "email": [("open_rate", 0.25), ("click_rate", 0.06)],
            "sms": [("click_rate", 0.09), ("conversion_rate", 0.03)],
            "ad": [("click_rate", 0.04), ("cost_per_click", 0.45)],
        }

        for channel, metrics in metrics_data.items():
            campaign_id = f"summer-promo-{channel}"
            for metric_type, value in metrics:
                call_tool(
                    log_metrics,
                    campaign_id=campaign_id,
                    variant_id="v1",
                    metric_type=metric_type,
                    value=value,
                )

        # 5. Verify metrics stored for each campaign
        for channel in ["email", "sms", "ad"]:
            campaign_id = f"summer-promo-{channel}"
            metrics_path = tmp_data_dir / "campaigns" / campaign_id / "metrics.json"
            assert metrics_path.exists()
            metrics = json.loads(metrics_path.read_text())
            assert len(metrics) >= 2

    def test_manifest_links_all_campaigns(self, tmp_data_dir):
        """Manifest should contain all campaign IDs for cross-reference."""
        call_tool(
            plan_multi_channel_campaign,
            name="black-friday",
            brief="Black Friday campaign",
            channels="email,sms,ad,seo",
        )

        manifest = json.loads(
            (tmp_data_dir / "orchestration" / "manifests" / "black-friday.json").read_text()
        )
        assert len(manifest["campaign_ids"]) == 4
        assert set(manifest["channels"]) == {"email", "sms", "ad", "seo"}

        # All campaign dirs should exist
        for cid in manifest["campaign_ids"]:
            assert (tmp_data_dir / "campaigns" / cid).exists()
