"""
Tests for tools/cross_channel_tools.py — learning transfer pipeline.
"""

import json

import pytest

from tests.conftest import call_tool
from tools.cross_channel_tools import (
    apply_cross_channel_transfer,
    evaluate_cross_channel_transfer,
    review_transfer_results,
)


# =========================================================================
# Helpers
# =========================================================================

def _seed_transferable_learning(tmp_data_dir, learning_id="learn_001"):
    """Seed a medium-confidence email learning eligible for transfer."""
    playbook = {
        "learnings": [
            {
                "id": learning_id,
                "category": "email",
                "subcategory": "tone",
                "learning": "Playful tone increases engagement by 15%",
                "evidence": ["spring-sale/v2"],
                "confidence": 0.65,
                "times_confirmed": 2,
                "first_observed": "2026-03-28",
                "last_confirmed": "2026-04-01",
                "tags": ["tone", "engagement"],
            }
        ]
    }
    (tmp_data_dir / "playbook.json").write_text(
        json.dumps(playbook, indent=2), encoding="utf-8"
    )
    return learning_id


def _seed_nontransferable_learning(tmp_data_dir, learning_id="learn_notransfer"):
    """Seed a learning with content_length category (no transfer targets)."""
    playbook = {
        "learnings": [
            {
                "id": learning_id,
                "category": "email",
                "subcategory": "content_length",
                "learning": "Emails under 100 words get more clicks",
                "evidence": ["test/v1"],
                "confidence": 0.7,
                "times_confirmed": 3,
                "tags": ["content-length"],
            }
        ]
    }
    (tmp_data_dir / "playbook.json").write_text(
        json.dumps(playbook, indent=2), encoding="utf-8"
    )
    return learning_id


# =========================================================================
# evaluate_cross_channel_transfer
# =========================================================================

class TestEvaluateCrossChannelTransfer:
    def test_creates_transfer_proposals(self, tmp_data_dir):
        learning_id = _seed_transferable_learning(tmp_data_dir)
        result = call_tool(evaluate_cross_channel_transfer, learning_id)
        assert "proposed" in result.lower() or "transfer" in result.lower()

        # Should have created transfer files
        transfers_dir = tmp_data_dir / "orchestration" / "transfers"
        transfer_files = list(transfers_dir.glob("transfer-*.json"))
        assert len(transfer_files) >= 1

        # Each should target a non-email channel
        for tf in transfer_files:
            data = json.loads(tf.read_text())
            assert data["source_channel"] == "email"
            assert data["target_channel"] != "email"
            assert data["status"] == "proposed"

    def test_nonexistent_learning_returns_error(self, tmp_data_dir):
        result = call_tool(evaluate_cross_channel_transfer, "fake_id")
        assert "Error" in result

    def test_low_confidence_rejected(self, tmp_data_dir):
        """Learning below 0.5 confidence and <2 confirmations should be rejected."""
        playbook = {
            "learnings": [{
                "id": "low_conf",
                "category": "email",
                "subcategory": "tone",
                "learning": "Unconfirmed pattern",
                "confidence": 0.3,
                "times_confirmed": 1,
            }]
        }
        (tmp_data_dir / "playbook.json").write_text(json.dumps(playbook))
        result = call_tool(evaluate_cross_channel_transfer, "low_conf")
        assert "confidence" in result.lower() or "needs" in result.lower()

    def test_nontransferable_category(self, tmp_data_dir):
        """content_length has empty targets — should say no transfer."""
        learning_id = _seed_nontransferable_learning(tmp_data_dir)
        result = call_tool(evaluate_cross_channel_transfer, learning_id)
        assert "does not transfer" in result.lower() or "no" in result.lower()

    def test_no_duplicate_proposals(self, tmp_data_dir):
        """Running evaluate twice should not create duplicate transfers."""
        learning_id = _seed_transferable_learning(tmp_data_dir)
        call_tool(evaluate_cross_channel_transfer, learning_id)
        count_1 = len(list((tmp_data_dir / "orchestration" / "transfers").glob("transfer-*.json")))

        result = call_tool(evaluate_cross_channel_transfer, learning_id)
        count_2 = len(list((tmp_data_dir / "orchestration" / "transfers").glob("transfer-*.json")))

        assert count_2 == count_1
        assert "already" in result.lower()


# =========================================================================
# apply_cross_channel_transfer
# =========================================================================

class TestApplyCrossChannelTransfer:
    def test_creates_validation_campaign(self, tmp_data_dir):
        learning_id = _seed_transferable_learning(tmp_data_dir)
        call_tool(evaluate_cross_channel_transfer, learning_id)

        # Find a transfer
        transfers_dir = tmp_data_dir / "orchestration" / "transfers"
        transfer_file = list(transfers_dir.glob("transfer-*.json"))[0]
        transfer = json.loads(transfer_file.read_text())
        transfer_id = transfer["transfer_id"]

        result = call_tool(apply_cross_channel_transfer, transfer_id)
        assert "validation campaign" in result.lower() or transfer_id in result

        # Transfer status should be "testing"
        updated = json.loads(transfer_file.read_text())
        assert updated["status"] == "testing"
        assert updated["validation_campaign_id"] is not None

        # Validation campaign dir should exist
        campaign_dir = tmp_data_dir / "campaigns" / updated["validation_campaign_id"]
        assert campaign_dir.exists()
        assert (campaign_dir / "brief.json").exists()

    def test_nonexistent_transfer_returns_error(self, tmp_data_dir):
        result = call_tool(apply_cross_channel_transfer, "fake-transfer")
        assert "Error" in result

    def test_non_proposed_transfer_returns_error(self, tmp_data_dir):
        """Applying an already-testing transfer should fail."""
        transfer = {
            "transfer_id": "already-testing",
            "status": "testing",
            "learning_id": "x",
        }
        (tmp_data_dir / "orchestration" / "transfers" / "already-testing.json").write_text(
            json.dumps(transfer)
        )
        result = call_tool(apply_cross_channel_transfer, "already-testing")
        assert "Error" in result


# =========================================================================
# review_transfer_results
# =========================================================================

class TestReviewTransferResults:
    def _setup_completed_transfer(self, tmp_data_dir, winner="treatment"):
        """Create a transfer in 'testing' with a COMPLETED A/B test."""
        transfer_id = "review-test-transfer"
        campaign_id = f"xfer-{transfer_id}-sms"

        # Transfer file
        transfer = {
            "transfer_id": transfer_id,
            "learning_id": "learn_001",
            "learning_text": "Playful tone increases engagement",
            "source_channel": "email",
            "target_channel": "sms",
            "status": "testing",
            "validation_campaign_id": campaign_id,
            "hypothesis": "Playful tone works for SMS too",
        }
        (tmp_data_dir / "orchestration" / "transfers" / f"{transfer_id}.json").write_text(
            json.dumps(transfer, indent=2)
        )

        # Campaign with COMPLETED ab_test_state
        campaign_dir = tmp_data_dir / "campaigns" / campaign_id
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "brief.json").write_text(json.dumps({
            "campaign_id": campaign_id, "channel": "sms"
        }))
        state = {
            "state": "COMPLETED",
            "winner": f"{winner}_variant",
            "result": {
                "verdict": f"winner_{winner}",
                "effect_size": 0.12,
                "p_value": 0.003,
            },
        }
        (campaign_dir / "ab_test_state.json").write_text(json.dumps(state))

        # Seed playbook with the learning
        _seed_transferable_learning(tmp_data_dir, "learn_001")

        return transfer_id

    def test_confirmed_transfer_updates_status(self, tmp_data_dir):
        transfer_id = self._setup_completed_transfer(tmp_data_dir, winner="treatment")
        result = call_tool(review_transfer_results, transfer_id)
        assert "CONFIRMED" in result

        transfer = json.loads(
            (tmp_data_dir / "orchestration" / "transfers" / f"{transfer_id}.json").read_text()
        )
        assert transfer["status"] == "confirmed"

    def test_confirmed_transfer_boosts_confidence(self, tmp_data_dir):
        transfer_id = self._setup_completed_transfer(tmp_data_dir, winner="treatment")
        playbook_before = json.loads((tmp_data_dir / "playbook.json").read_text())
        conf_before = playbook_before["learnings"][0]["confidence"]

        call_tool(review_transfer_results, transfer_id)

        playbook_after = json.loads((tmp_data_dir / "playbook.json").read_text())
        conf_after = playbook_after["learnings"][0]["confidence"]
        assert conf_after == pytest.approx(conf_before + 0.05, abs=0.01)

    def test_rejected_transfer_when_control_wins(self, tmp_data_dir):
        transfer_id = self._setup_completed_transfer(tmp_data_dir, winner="control")
        result = call_tool(review_transfer_results, transfer_id)
        assert "REJECTED" in result

        transfer = json.loads(
            (tmp_data_dir / "orchestration" / "transfers" / f"{transfer_id}.json").read_text()
        )
        assert transfer["status"] == "rejected"

    def test_nonexistent_transfer_returns_error(self, tmp_data_dir):
        result = call_tool(review_transfer_results, "no-such-transfer")
        assert "Error" in result

    def test_non_testing_transfer_returns_error(self, tmp_data_dir):
        transfer = {"transfer_id": "not-testing", "status": "proposed"}
        (tmp_data_dir / "orchestration" / "transfers" / "not-testing.json").write_text(
            json.dumps(transfer)
        )
        result = call_tool(review_transfer_results, "not-testing")
        assert "testing" in result.lower()

    def test_still_in_progress_returns_message(self, tmp_data_dir):
        """If the validation test is still COLLECTING, should say in progress."""
        transfer_id = "inprog-transfer"
        campaign_id = f"xfer-{transfer_id}-ad"

        (tmp_data_dir / "orchestration" / "transfers" / f"{transfer_id}.json").write_text(
            json.dumps({
                "transfer_id": transfer_id,
                "status": "testing",
                "validation_campaign_id": campaign_id,
            })
        )
        campaign_dir = tmp_data_dir / "campaigns" / campaign_id
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "ab_test_state.json").write_text(json.dumps({
            "state": "COLLECTING",
        }))

        result = call_tool(review_transfer_results, transfer_id)
        assert "in progress" in result.lower() or "still" in result.lower()
