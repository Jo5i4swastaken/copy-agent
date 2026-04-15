"""
Integration test: Cross-channel learning transfer flow.

save_learning → evaluate_cross_channel_transfer → apply_cross_channel_transfer
→ simulate A/B test result → review_transfer_results → verify confidence bump.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.analysis_tools import save_learning
from tools.cross_channel_tools import (
    evaluate_cross_channel_transfer,
    apply_cross_channel_transfer,
    review_transfer_results,
)


def _seed_learning(tmp_data_dir, learning_id="learn_001", confidence=0.65,
                   times_confirmed=2, category="email", subcategory="tone"):
    """Seed a playbook with a single learning eligible for transfer."""
    playbook = {
        "learnings": [
            {
                "id": learning_id,
                "category": category,
                "subcategory": subcategory,
                "learning": "Playful tone increases click-through by 15%",
                "evidence": "spring-sale/v2",
                "confidence": confidence,
                "times_confirmed": times_confirmed,
                "times_contradicted": 0,
                "first_observed": "2026-03-28",
                "last_confirmed": "2026-04-01",
                "tags": ["tone", "engagement", "playful"],
            }
        ]
    }
    (tmp_data_dir / "playbook.json").write_text(
        json.dumps(playbook, indent=2), encoding="utf-8"
    )
    return learning_id


def _simulate_completed_ab_test(tmp_data_dir, campaign_id, winner="treatment"):
    """Write a COMPLETED ab_test_state.json for a validation campaign."""
    campaign_dir = tmp_data_dir / "campaigns" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    (campaign_dir / "brief.json").write_text(json.dumps({
        "campaign_id": campaign_id, "channel": "sms",
    }))

    state = {
        "state": "COMPLETED",
        "winner": f"{winner}_variant",
        "result": {
            "verdict": f"winner_{winner}",
            "winner_variant": f"{winner}_variant",
            "effect_size": 0.12,
            "p_value": 0.003,
            "control_mean": 0.05,
            "treatment_mean": 0.17,
            "relative_lift": 240.0,
        },
    }
    (campaign_dir / "ab_test_state.json").write_text(json.dumps(state, indent=2))


class TestCrossChannelFlow:
    """End-to-end: learning → evaluate → apply → review → playbook update."""

    def test_full_transfer_confirmed(self, tmp_data_dir):
        learning_id = _seed_learning(tmp_data_dir)

        # 1. Evaluate — should propose transfers to sms, ad, seo
        result = call_tool(evaluate_cross_channel_transfer, learning_id)
        assert "proposed" in result.lower() or "transfer" in result.lower()

        # Find the created transfer files
        transfers_dir = tmp_data_dir / "orchestration" / "transfers"
        transfer_files = list(transfers_dir.glob("transfer-*.json"))
        assert len(transfer_files) >= 1

        # Pick the first transfer
        transfer = json.loads(transfer_files[0].read_text())
        transfer_id = transfer["transfer_id"]
        assert transfer["status"] == "proposed"
        assert transfer["source_channel"] == "email"
        assert transfer["target_channel"] != "email"

        # 2. Apply — creates a validation campaign
        result = call_tool(apply_cross_channel_transfer, transfer_id)
        assert "validation" in result.lower() or transfer_id in result

        # Transfer should now be "testing"
        transfer = json.loads(transfer_files[0].read_text())
        assert transfer["status"] == "testing"
        campaign_id = transfer["validation_campaign_id"]
        assert (tmp_data_dir / "campaigns" / campaign_id).exists()

        # 3. Simulate a completed A/B test where treatment won
        _simulate_completed_ab_test(tmp_data_dir, campaign_id, winner="treatment")

        # Record confidence before review
        playbook = json.loads((tmp_data_dir / "playbook.json").read_text())
        conf_before = playbook["learnings"][0]["confidence"]

        # 4. Review — should confirm the transfer and boost confidence
        result = call_tool(review_transfer_results, transfer_id)
        assert "CONFIRMED" in result

        # Verify transfer status updated
        transfer = json.loads(transfer_files[0].read_text())
        assert transfer["status"] == "confirmed"

        # Verify confidence boosted (+0.05)
        playbook = json.loads((tmp_data_dir / "playbook.json").read_text())
        conf_after = playbook["learnings"][0]["confidence"]
        assert conf_after == pytest.approx(conf_before + 0.05, abs=0.01)

        # Verify cross_channel_evidence appended
        evidence = playbook["learnings"][0].get("cross_channel_evidence", [])
        assert len(evidence) >= 1
        assert evidence[0]["confirmed"] is True

    def test_transfer_rejected_when_control_wins(self, tmp_data_dir):
        learning_id = _seed_learning(tmp_data_dir)

        call_tool(evaluate_cross_channel_transfer, learning_id)

        transfers_dir = tmp_data_dir / "orchestration" / "transfers"
        transfer_file = list(transfers_dir.glob("transfer-*.json"))[0]
        transfer = json.loads(transfer_file.read_text())
        transfer_id = transfer["transfer_id"]

        call_tool(apply_cross_channel_transfer, transfer_id)
        transfer = json.loads(transfer_file.read_text())
        campaign_id = transfer["validation_campaign_id"]

        # Simulate control winning
        _simulate_completed_ab_test(tmp_data_dir, campaign_id, winner="control")

        playbook_before = json.loads((tmp_data_dir / "playbook.json").read_text())
        conf_before = playbook_before["learnings"][0]["confidence"]

        result = call_tool(review_transfer_results, transfer_id)
        assert "REJECTED" in result

        transfer = json.loads(transfer_file.read_text())
        assert transfer["status"] == "rejected"

        # Confidence should NOT increase
        playbook_after = json.loads((tmp_data_dir / "playbook.json").read_text())
        conf_after = playbook_after["learnings"][0]["confidence"]
        assert conf_after == conf_before

    def test_no_duplicate_transfers(self, tmp_data_dir):
        """Running evaluate twice should not create duplicate transfers."""
        learning_id = _seed_learning(tmp_data_dir)

        call_tool(evaluate_cross_channel_transfer, learning_id)
        transfers_dir = tmp_data_dir / "orchestration" / "transfers"
        count_1 = len(list(transfers_dir.glob("transfer-*.json")))

        result = call_tool(evaluate_cross_channel_transfer, learning_id)
        count_2 = len(list(transfers_dir.glob("transfer-*.json")))

        assert count_2 == count_1
        assert "already" in result.lower()

    def test_low_confidence_learning_blocked(self, tmp_data_dir):
        """Learning below threshold should not be evaluated for transfer."""
        _seed_learning(tmp_data_dir, confidence=0.3, times_confirmed=1)
        result = call_tool(evaluate_cross_channel_transfer, "learn_001")
        assert "confidence" in result.lower() or "needs" in result.lower()

        # No transfer files should be created
        transfers_dir = tmp_data_dir / "orchestration" / "transfers"
        assert len(list(transfers_dir.glob("transfer-*.json"))) == 0

    def test_full_flow_from_save_learning_to_transfer(self, tmp_data_dir):
        """Start from save_learning (not seeded), then evaluate for transfer."""
        # Save a learning via the tool
        result = call_tool(
            save_learning,
            category="email",
            learning="Urgency-based CTAs boost conversion by 20%",
            evidence="summer-sale/v1",
            confidence="medium",
        )
        assert "saved" in result.lower()

        # The new learning gets ID learn_001 and subcategory is derived from tags.
        # Since subcategory isn't set by save_learning, it defaults to the category.
        # The transferability matrix uses "general" fallback for unknown categories.
        playbook = json.loads((tmp_data_dir / "playbook.json").read_text())
        learning_id = playbook["learnings"][0]["id"]

        # Manually set subcategory to "urgency" (in production the agent would do this)
        playbook["learnings"][0]["subcategory"] = "urgency"
        playbook["learnings"][0]["times_confirmed"] = 2
        (tmp_data_dir / "playbook.json").write_text(
            json.dumps(playbook, indent=2), encoding="utf-8"
        )

        result = call_tool(evaluate_cross_channel_transfer, learning_id)
        assert "proposed" in result.lower() or "transfer" in result.lower()
