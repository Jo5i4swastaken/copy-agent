"""
Tests for tools/orchestration_tools.py — multi-channel campaign planning and dispatch.
"""

import json
from unittest.mock import patch

import pytest

from tests.conftest import call_tool
from tools.orchestration_tools import (
    dispatch_to_specialist,
    list_active_tests,
    plan_multi_channel_campaign,
)


# =========================================================================
# plan_multi_channel_campaign
# =========================================================================

class TestPlanMultiChannelCampaign:
    def test_creates_campaign_per_channel(self, tmp_data_dir):
        result = call_tool(
            plan_multi_channel_campaign,
            name="spring-sale",
            brief="Promote our spring sale across channels",
            channels="email,sms,ad",
        )
        assert "spring-sale" in result
        assert "3" in result  # 3 campaigns created

        for channel in ["email", "sms", "ad"]:
            campaign_dir = tmp_data_dir / "campaigns" / f"spring-sale-{channel}"
            assert campaign_dir.exists(), f"Missing campaign dir for {channel}"
            brief = json.loads((campaign_dir / "brief.json").read_text())
            assert brief["channel"] == channel
            assert brief["multi_channel_group"] == "spring-sale"

    def test_creates_orchestration_manifest(self, tmp_data_dir):
        call_tool(
            plan_multi_channel_campaign,
            name="manifest-test",
            brief="Test brief",
            channels="email,seo",
        )
        manifest_path = tmp_data_dir / "orchestration" / "manifests" / "manifest-test.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["channels"] == ["email", "seo"]
        assert len(manifest["campaign_ids"]) == 2

    def test_invalid_channel_returns_error(self, tmp_data_dir):
        result = call_tool(
            plan_multi_channel_campaign,
            name="bad",
            brief="Brief",
            channels="email,twitter",
        )
        assert "Error" in result
        assert "twitter" in result

    def test_empty_channels_returns_error(self, tmp_data_dir):
        result = call_tool(
            plan_multi_channel_campaign,
            name="empty",
            brief="Brief",
            channels="",
        )
        assert "Error" in result

    def test_empty_name_returns_error(self, tmp_data_dir):
        result = call_tool(
            plan_multi_channel_campaign,
            name="",
            brief="Brief",
            channels="email",
        )
        assert "Error" in result

    def test_creates_empty_variants_json(self, tmp_data_dir):
        call_tool(
            plan_multi_channel_campaign,
            name="var-test",
            brief="Brief",
            channels="email",
        )
        variants = json.loads(
            (tmp_data_dir / "campaigns" / "var-test-email" / "variants.json").read_text()
        )
        assert variants == []

    def test_audience_and_constraints_stored(self, tmp_data_dir):
        call_tool(
            plan_multi_channel_campaign,
            name="meta-test",
            brief="Brief",
            channels="sms",
            audience="Young professionals",
            constraints="No slang",
        )
        brief = json.loads(
            (tmp_data_dir / "campaigns" / "meta-test-sms" / "brief.json").read_text()
        )
        assert brief["audience"] == "Young professionals"
        assert brief["constraints"] == "No slang"


# =========================================================================
# dispatch_to_specialist
# =========================================================================

class TestDispatchToSpecialist:
    def test_nonexistent_campaign_returns_error(self, tmp_data_dir):
        result = call_tool(dispatch_to_specialist, "fake-campaign")
        assert "Error" in result

    def test_invalid_channel_returns_error(self, tmp_data_dir):
        # Create a campaign with no channel in brief
        campaign_dir = tmp_data_dir / "campaigns" / "no-channel"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": "no-channel", "brief": "Test", "channel": "invalid"
        }))
        result = call_tool(dispatch_to_specialist, "no-channel")
        assert "Error" in result

    def test_dispatch_catches_specialist_error(self, tmp_data_dir):
        """If the specialist raises an exception, dispatch should catch it."""
        campaign_dir = tmp_data_dir / "campaigns" / "error-camp"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": "error-camp", "brief": "Test", "channel": "email"
        }))
        (campaign_dir / "variants.json").write_text("[]")

        # Mock the specialist to raise an error
        with patch("tools.orchestration_tools._log_dispatch"):
            with patch(
                "tools.specialists.email_specialist.specialist_email",
                side_effect=Exception("LLM timeout"),
            ):
                result = call_tool(dispatch_to_specialist, "error-camp", "email")
                assert "Error" in result or "failed" in result.lower()


# =========================================================================
# list_active_tests (orchestration version)
# =========================================================================

class TestListActiveTestsOrch:
    def test_no_tests_returns_message(self, tmp_data_dir):
        result = call_tool(list_active_tests)
        assert "No active" in result or "No campaigns" in result

    def test_lists_collecting_test(self, seed_ab_test, tmp_data_dir):
        result = call_tool(list_active_tests)
        campaign_id, test_id = seed_ab_test
        assert test_id in result
        assert "COLLECTING" in result

    def test_excludes_completed(self, tmp_data_dir):
        campaign_dir = tmp_data_dir / "campaigns" / "done-camp"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "ab_test_state.json").write_text(json.dumps({
            "test_id": "done-test",
            "campaign_id": "done-camp",
            "state": "COMPLETED",
        }))
        result = call_tool(list_active_tests)
        assert "done-test" not in result
