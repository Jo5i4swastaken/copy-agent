"""
Tests for tools/copy_tools.py — campaign creation and variant storage.

Uses the tmp_data_dir fixture to monkeypatch DATA_DIR/CAMPAIGNS_DIR so
all file I/O goes to a temporary directory.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.copy_tools import generate_copy, get_campaign, list_campaigns, save_copy_variant


# =========================================================================
# generate_copy
# =========================================================================

class TestGenerateCopy:
    def test_creates_campaign_directory(self, tmp_data_dir):
        result = call_tool(generate_copy, "Test brief", "email", 3, "spring-sale")
        assert "spring-sale" in result
        campaign_dir = tmp_data_dir / "campaigns" / "spring-sale"
        assert campaign_dir.exists()

    def test_creates_brief_json(self, tmp_data_dir):
        call_tool(generate_copy, "Test brief", "email", 3, "my-campaign")
        brief_path = tmp_data_dir / "campaigns" / "my-campaign" / "brief.json"
        assert brief_path.exists()
        brief = json.loads(brief_path.read_text())
        assert brief["campaign_id"] == "my-campaign"
        assert brief["channel"] == "email"
        assert brief["num_variants"] == 3
        assert brief["status"] == "draft"
        assert brief["brief"] == "Test brief"

    def test_creates_empty_variants_json(self, tmp_data_dir):
        call_tool(generate_copy, "Brief", "sms", 2, "sms-promo")
        variants_path = tmp_data_dir / "campaigns" / "sms-promo" / "variants.json"
        assert variants_path.exists()
        variants = json.loads(variants_path.read_text())
        assert variants == []

    def test_invalid_channel_returns_error(self, tmp_data_dir):
        result = call_tool(generate_copy, "Brief", "twitter", 2, "bad-channel")
        assert "Error" in result
        assert "Invalid channel" in result

    def test_auto_id_when_no_name(self, tmp_data_dir):
        result = call_tool(generate_copy, "Brief", "email", 2, "")
        assert "campaign-" in result  # auto-generated ID

    def test_slugifies_campaign_name(self, tmp_data_dir):
        result = call_tool(generate_copy, "Brief", "email", 2, "Spring Sale 2026!")
        assert "spring-sale-2026" in result

    def test_unique_suffix_on_duplicate(self, tmp_data_dir):
        call_tool(generate_copy, "Brief 1", "email", 2, "dupe-test")
        result = call_tool(generate_copy, "Brief 2", "email", 2, "dupe-test")
        # Second campaign should get a suffix
        assert "dupe-test-2" in result
        assert (tmp_data_dir / "campaigns" / "dupe-test").exists()
        assert (tmp_data_dir / "campaigns" / "dupe-test-2").exists()

    def test_channel_specific_guidance_in_output(self, tmp_data_dir):
        result = call_tool(generate_copy, "Brief", "seo", 2, "seo-test")
        assert "meta title" in result.lower() or "meta description" in result.lower()

    def test_returns_call_to_action_for_save(self, tmp_data_dir):
        result = call_tool(generate_copy, "Brief", "email", 3, "cta-test")
        assert "save_copy_variant" in result


# =========================================================================
# save_copy_variant
# =========================================================================

class TestSaveCopyVariant:
    def test_saves_variant_to_json(self, tmp_data_dir):
        call_tool(generate_copy, "Brief", "email", 2, "save-test")
        result = call_tool(
            save_copy_variant,
            campaign_id="save-test",
            variant_id="v1",
            channel="email",
            content="Check out our spring deals!",
            subject_line="Spring Deals Inside",
            cta="Shop Now",
            tone="urgent",
        )
        assert "v1" in result
        assert "save-test" in result

        variants = json.loads(
            (tmp_data_dir / "campaigns" / "save-test" / "variants.json").read_text()
        )
        assert len(variants) == 1
        assert variants[0]["variant_id"] == "v1"
        assert variants[0]["content"] == "Check out our spring deals!"
        assert variants[0]["subject_line"] == "Spring Deals Inside"

    def test_appends_multiple_variants(self, tmp_data_dir):
        call_tool(generate_copy, "Brief", "email", 3, "multi-var")
        call_tool(save_copy_variant, "multi-var", "v1", "email", "Content A")
        call_tool(save_copy_variant, "multi-var", "v2", "email", "Content B")
        call_tool(save_copy_variant, "multi-var", "v3", "email", "Content C")

        variants = json.loads(
            (tmp_data_dir / "campaigns" / "multi-var" / "variants.json").read_text()
        )
        assert len(variants) == 3
        assert [v["variant_id"] for v in variants] == ["v1", "v2", "v3"]

    def test_nonexistent_campaign_returns_error(self, tmp_data_dir):
        result = call_tool(save_copy_variant, "no-such-campaign", "v1", "email", "Content")
        assert "Error" in result
        assert "not found" in result

    def test_invalid_channel_returns_error(self, tmp_data_dir):
        call_tool(generate_copy, "Brief", "email", 2, "chan-test")
        result = call_tool(save_copy_variant, "chan-test", "v1", "twitter", "Content")
        assert "Error" in result
        assert "Invalid channel" in result

    def test_variant_has_draft_status(self, tmp_data_dir):
        call_tool(generate_copy, "Brief", "email", 1, "status-test")
        call_tool(save_copy_variant, "status-test", "v1", "email", "Content")

        variants = json.loads(
            (tmp_data_dir / "campaigns" / "status-test" / "variants.json").read_text()
        )
        assert variants[0]["status"] == "draft"

    def test_variant_total_count_in_result(self, tmp_data_dir):
        call_tool(generate_copy, "Brief", "email", 2, "count-test")
        call_tool(save_copy_variant, "count-test", "v1", "email", "A")
        result = call_tool(save_copy_variant, "count-test", "v2", "email", "B")
        assert "2" in result  # total variants count


# =========================================================================
# list_campaigns
# =========================================================================

class TestListCampaigns:
    def test_empty_returns_no_campaigns(self, tmp_data_dir):
        result = call_tool(list_campaigns)
        assert "No campaigns found" in result

    def test_lists_created_campaigns(self, tmp_data_dir):
        call_tool(generate_copy, "Brief A", "email", 2, "camp-a")
        call_tool(generate_copy, "Brief B", "sms", 2, "camp-b")
        result = call_tool(list_campaigns)
        assert "camp-a" in result
        assert "camp-b" in result
        assert "2 campaign" in result

    def test_filter_by_channel(self, tmp_data_dir):
        call_tool(generate_copy, "Brief A", "email", 2, "email-camp")
        call_tool(generate_copy, "Brief B", "sms", 2, "sms-camp")
        result = call_tool(list_campaigns, channel="email")
        assert "email-camp" in result
        assert "sms-camp" not in result

    def test_filter_by_status(self, tmp_data_dir):
        call_tool(generate_copy, "Brief", "email", 2, "draft-camp")
        result = call_tool(list_campaigns, status="draft")
        assert "draft-camp" in result

    def test_limit_parameter(self, tmp_data_dir):
        for i in range(5):
            call_tool(generate_copy, f"Brief {i}", "email", 1, f"camp-{i}")
        result = call_tool(list_campaigns, limit=2)
        assert "2 campaign" in result

    def test_sorted_newest_first(self, tmp_data_dir):
        call_tool(generate_copy, "Older", "email", 1, "older")
        call_tool(generate_copy, "Newer", "email", 1, "newer")
        result = call_tool(list_campaigns)
        # Newer should appear before older
        newer_pos = result.index("newer")
        older_pos = result.index("older")
        assert newer_pos < older_pos


# =========================================================================
# get_campaign
# =========================================================================

class TestGetCampaign:
    def test_returns_campaign_details(self, seed_campaign):
        result = call_tool(get_campaign, seed_campaign)
        assert "test-campaign" in result
        assert "email" in result
        assert "spring sale" in result.lower()

    def test_shows_variants(self, seed_campaign):
        result = call_tool(get_campaign, seed_campaign)
        assert "v1" in result
        assert "v2" in result
        assert "Spring Sale: 30% Off Everything" in result

    def test_shows_metrics_summary(self, seed_campaign):
        result = call_tool(get_campaign, seed_campaign)
        assert "Metrics" in result
        assert "open_rate" in result

    def test_nonexistent_campaign_returns_error(self, tmp_data_dir):
        result = call_tool(get_campaign, "nonexistent")
        assert "Error" in result
        assert "not found" in result
