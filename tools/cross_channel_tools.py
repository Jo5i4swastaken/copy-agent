"""
Cross-channel learning transfer tools for the Copy Agent.

When a learning is confirmed in one channel, these tools evaluate whether
it could apply to other channels, create validation tests, and review
transfer results.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from tools.lock import FileLock
from omniagents import function_tool

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PLAYBOOK_PATH = DATA_DIR / "playbook.json"
CAMPAIGNS_DIR = DATA_DIR / "campaigns"
TRANSFERS_DIR = DATA_DIR / "orchestration" / "transfers"

# ---------------------------------------------------------------------------
# Transferability matrix
# ---------------------------------------------------------------------------
# Maps learning categories/attributes to eligible target channels.
# "all" means it can transfer to any channel.
TRANSFERABILITY_MATRIX = {
    "tone": {"targets": "all", "type": "direct",
             "note": "Same tone, different format constraints"},
    "cta_style": {"targets": "all", "type": "direct",
                  "note": "Same CTA pattern, different context"},
    "urgency": {"targets": "all", "type": "direct",
                "note": "Psychological principle is channel-agnostic"},
    "scarcity": {"targets": "all", "type": "direct",
                 "note": "Psychological principle is channel-agnostic"},
    "subject_format": {"targets": {"ad", "sms"}, "type": "adapted",
                       "note": "Structural pattern, different length constraints"},
    "headline_format": {"targets": {"email", "sms", "seo"}, "type": "adapted",
                        "note": "Headline pattern adapted to channel format"},
    "personalization": {"targets": {"email", "sms"}, "type": "partial",
                        "note": "Only channels with 1:1 delivery"},
    "social_proof": {"targets": "all", "type": "direct",
                     "note": "Trust signals work across channels"},
    "content_length": {"targets": set(), "type": "none",
                       "note": "Channel constraints differ too much"},
    "send_timing": {"targets": set(), "type": "none",
                    "note": "Channel consumption patterns differ"},
    "general": {"targets": "all", "type": "direct",
                "note": "General learnings may apply broadly"},
}

ALL_CHANNELS = {"email", "sms", "ad", "seo"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def _get_learning_by_id(learning_id: str) -> dict | None:
    """Find a learning by ID in the playbook."""
    data = _load_json(PLAYBOOK_PATH)
    if data is None:
        return None
    for learning in data.get("learnings", []):
        if learning.get("id") == learning_id:
            return learning
    return None


def _get_eligible_channels(source_channel: str, category: str) -> list[str]:
    """Determine which channels a learning can transfer to."""
    rule = TRANSFERABILITY_MATRIX.get(category)
    if rule is None:
        # Default: try general rule
        rule = TRANSFERABILITY_MATRIX.get("general", {})

    targets = rule.get("targets", set())
    if targets == "all":
        targets = ALL_CHANNELS.copy()
    elif isinstance(targets, set):
        targets = targets.copy()
    else:
        targets = set()

    # Remove the source channel (don't transfer to self)
    targets.discard(source_channel)
    return sorted(targets)


# ---------------------------------------------------------------------------
# Tool 1: evaluate_cross_channel_transfer
# ---------------------------------------------------------------------------

@function_tool
def evaluate_cross_channel_transfer(learning_id: str) -> str:
    """Evaluate whether a confirmed learning could apply to other channels.

    Reads the learning from the playbook, checks the transferability matrix,
    and proposes transfer hypotheses for eligible target channels. Only
    evaluates learnings at medium confidence (0.5+) or confirmed 2+ times.

    Args:
        learning_id: The ID of the learning in the playbook to evaluate.

    Returns:
        Summary of proposed transfers or explanation of why no transfer applies.
    """
    learning = _get_learning_by_id(learning_id)
    if learning is None:
        return f"Error: Learning '{learning_id}' not found in playbook."

    confidence = learning.get("confidence", 0)
    times_confirmed = learning.get("times_confirmed", 0)

    if confidence < 0.5 and times_confirmed < 2:
        return (
            f"Learning '{learning_id}' has confidence {confidence} and "
            f"{times_confirmed} confirmations. It needs confidence >= 0.5 or "
            "2+ confirmations before cross-channel transfer is evaluated."
        )

    source_channel = learning.get("category", "general")
    learning_text = learning.get("learning", "")
    category = learning.get("subcategory", learning.get("category", "general"))

    eligible = _get_eligible_channels(source_channel, category)

    if not eligible:
        rule = TRANSFERABILITY_MATRIX.get(category, {})
        return (
            f"Learning '{learning_id}' (category: {category}) does not transfer "
            f"to other channels. Reason: {rule.get('note', 'Channel-specific learning')}."
        )

    # Check for existing transfers to avoid duplicates
    existing_transfers = _list_transfers_for_learning(learning_id)
    already_targeted = {t.get("target_channel") for t in existing_transfers}
    new_targets = [c for c in eligible if c not in already_targeted]

    if not new_targets:
        return (
            f"Learning '{learning_id}' already has transfer proposals for all "
            f"eligible channels: {', '.join(eligible)}."
        )

    # Create transfer hypotheses
    transfers_created = []
    rule = TRANSFERABILITY_MATRIX.get(category, TRANSFERABILITY_MATRIX["general"])
    transfer_type = rule.get("type", "direct")

    for target in new_targets:
        transfer_id = f"transfer-{uuid.uuid4().hex[:8]}"
        hypothesis = _generate_hypothesis(learning_text, source_channel, target, transfer_type)

        transfer = {
            "transfer_id": transfer_id,
            "learning_id": learning_id,
            "learning_text": learning_text,
            "source_channel": source_channel,
            "target_channel": target,
            "transfer_type": transfer_type,
            "hypothesis": hypothesis,
            "status": "proposed",
            "created_at": datetime.now().isoformat(),
            "validation_campaign_id": None,
            "validation_test_id": None,
            "result": None,
        }
        _save_json(TRANSFERS_DIR / f"{transfer_id}.json", transfer)
        transfers_created.append(transfer)

    # Format output
    lines = [
        "=" * 60,
        f"CROSS-CHANNEL TRANSFER EVALUATION: {learning_id}",
        "=" * 60,
        f"Source: {source_channel} (confidence: {confidence})",
        f"Learning: {learning_text}",
        f"Transfer type: {transfer_type}",
        "",
        f"Proposed transfers ({len(transfers_created)}):",
    ]

    for t in transfers_created:
        lines.append(f"  - {t['transfer_id']}: {source_channel} → {t['target_channel']}")
        lines.append(f"    Hypothesis: {t['hypothesis']}")

    lines.append("")
    lines.append("Next: Use apply_cross_channel_transfer(transfer_id) to create a validation A/B test.")
    lines.append("=" * 60)

    return "\n".join(lines)


def _generate_hypothesis(learning: str, source: str, target: str, transfer_type: str) -> str:
    """Generate a human-readable transfer hypothesis."""
    if transfer_type == "direct":
        return f"The pattern '{learning}' observed in {source} will also improve {target} performance."
    elif transfer_type == "adapted":
        return f"An adapted version of '{learning}' from {source} will improve {target} performance when adjusted for {target} format constraints."
    else:
        return f"The insight '{learning}' from {source} may partially apply to {target}."


def _list_transfers_for_learning(learning_id: str) -> list[dict]:
    """List all transfer proposals for a given learning."""
    if not TRANSFERS_DIR.exists():
        return []
    transfers = []
    for tf in TRANSFERS_DIR.iterdir():
        if tf.suffix != ".json":
            continue
        data = _load_json(tf)
        if data and data.get("learning_id") == learning_id:
            transfers.append(data)
    return transfers


# ---------------------------------------------------------------------------
# Tool 2: apply_cross_channel_transfer
# ---------------------------------------------------------------------------

@function_tool
def apply_cross_channel_transfer(transfer_id: str) -> str:
    """Create a validation campaign and A/B test for a transfer hypothesis.

    Takes a proposed transfer, creates a new campaign in the target channel,
    and sets up an A/B test to validate whether the transferred learning
    actually works in the new channel.

    Args:
        transfer_id: The ID of the transfer proposal to validate.

    Returns:
        Details of the created validation campaign and test setup.
    """
    transfer_path = TRANSFERS_DIR / f"{transfer_id}.json"
    transfer = _load_json(transfer_path)
    if transfer is None:
        return f"Error: Transfer '{transfer_id}' not found."

    if transfer.get("status") != "proposed":
        return (
            f"Error: Transfer '{transfer_id}' is in status '{transfer.get('status')}'. "
            "Only 'proposed' transfers can be applied."
        )

    target_channel = transfer.get("target_channel", "")
    hypothesis = transfer.get("hypothesis", "")
    learning_text = transfer.get("learning_text", "")
    now = datetime.now().isoformat()

    # Create validation campaign
    campaign_id = f"xfer-{transfer_id}-{target_channel}"
    campaign_dir = CAMPAIGNS_DIR / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)

    brief = {
        "campaign_id": campaign_id,
        "name": f"Cross-channel validation: {transfer_id}",
        "channel": target_channel,
        "brief": (
            f"Validate cross-channel transfer: {hypothesis}\n\n"
            f"Original learning: {learning_text}\n"
            f"Source channel: {transfer.get('source_channel')}\n"
            f"Generate a control variant (standard approach) and a treatment "
            f"variant (applying the transferred learning)."
        ),
        "audience": "",
        "constraints": f"This is a cross-channel validation test for transfer {transfer_id}.",
        "status": "draft",
        "created_at": now,
        "transfer_id": transfer_id,
    }
    _save_json(campaign_dir / "brief.json", brief)
    _save_json(campaign_dir / "variants.json", [])

    # Update transfer status
    transfer["status"] = "testing"
    transfer["validation_campaign_id"] = campaign_id
    transfer["applied_at"] = now
    _save_json(transfer_path, transfer)

    lines = [
        "=" * 60,
        f"CROSS-CHANNEL TRANSFER APPLIED: {transfer_id}",
        "=" * 60,
        f"Target channel: {target_channel}",
        f"Validation campaign: {campaign_id}",
        f"Hypothesis: {hypothesis}",
        "",
        "Next steps:",
        f"  1. Use dispatch_to_specialist('{campaign_id}', '{target_channel}') to generate variants.",
        f"  2. Use design_ab_test for campaign '{campaign_id}' to set up the validation test.",
        f"  3. Use start_ab_test to begin testing.",
        f"  4. After test concludes, use review_transfer_results('{transfer_id}').",
        "=" * 60,
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 3: review_transfer_results
# ---------------------------------------------------------------------------

@function_tool
def review_transfer_results(transfer_id: str) -> str:
    """Review the results of a cross-channel transfer validation test.

    Checks if the validation A/B test has concluded and updates the
    transfer status and playbook learning confidence accordingly.

    Args:
        transfer_id: The ID of the transfer to review.

    Returns:
        Summary of the transfer validation results.
    """
    transfer_path = TRANSFERS_DIR / f"{transfer_id}.json"
    transfer = _load_json(transfer_path)
    if transfer is None:
        return f"Error: Transfer '{transfer_id}' not found."

    if transfer.get("status") != "testing":
        return (
            f"Transfer '{transfer_id}' is in status '{transfer.get('status')}'. "
            "Only 'testing' transfers can be reviewed."
        )

    campaign_id = transfer.get("validation_campaign_id", "")
    if not campaign_id:
        return f"Error: Transfer '{transfer_id}' has no validation campaign."

    # Check if the A/B test has concluded
    state_path = CAMPAIGNS_DIR / campaign_id / "ab_test_state.json"
    state = _load_json(state_path)

    if state is None:
        return (
            f"No A/B test state found for campaign '{campaign_id}'. "
            "Has the validation test been started with start_ab_test?"
        )

    test_state = state.get("state", "")

    if test_state in ("COLLECTING", "WAITING", "ANALYZING", "DEPLOYING"):
        return (
            f"Transfer '{transfer_id}' validation test is still in progress "
            f"(state: {test_state}). Check again after the test concludes."
        )

    now = datetime.now().isoformat()

    if test_state == "DECIDED" or test_state == "COMPLETED":
        winner = state.get("winner", "")
        result = state.get("result", {})

        # Check if the treatment (transferred learning) won
        treatment_won = "treatment" in str(winner).lower()

        if treatment_won:
            transfer["status"] = "confirmed"
            transfer["result"] = "confirmed"
            transfer["result_detail"] = (
                f"Treatment (transferred learning) won. "
                f"Effect size: {result.get('effect_size', 'N/A')}, "
                f"p-value: {result.get('p_value', 'N/A')}."
            )
            # Update playbook: boost the learning's cross-channel evidence
            _update_playbook_with_transfer(transfer, confirmed=True)
        else:
            transfer["status"] = "rejected"
            transfer["result"] = "rejected"
            transfer["result_detail"] = (
                f"Control won or no significant difference. "
                f"The learning does not transfer to {transfer.get('target_channel')}."
            )
            _update_playbook_with_transfer(transfer, confirmed=False)

    elif test_state == "INCONCLUSIVE":
        transfer["status"] = "inconclusive"
        transfer["result"] = "inconclusive"
        transfer["result_detail"] = "Test was inconclusive. Consider extending or retesting."

    else:
        return f"Unexpected test state: {test_state}."

    transfer["reviewed_at"] = now
    _save_json(transfer_path, transfer)

    lines = [
        "=" * 60,
        f"TRANSFER REVIEW: {transfer_id}",
        "=" * 60,
        f"Source: {transfer.get('source_channel')} → Target: {transfer.get('target_channel')}",
        f"Hypothesis: {transfer.get('hypothesis', '')}",
        f"Result: {transfer.get('result', '').upper()}",
        f"Detail: {transfer.get('result_detail', '')}",
        "=" * 60,
    ]

    return "\n".join(lines)


def _update_playbook_with_transfer(transfer: dict, confirmed: bool) -> None:
    """Update the playbook learning with cross-channel transfer evidence."""
    if not PLAYBOOK_PATH.exists():
        return

    lock_path = PLAYBOOK_PATH.with_suffix(PLAYBOOK_PATH.suffix + ".lock")
    with FileLock(str(lock_path)):
        try:
            with open(PLAYBOOK_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        for learning in data.get("learnings", []):
            if learning.get("id") == transfer.get("learning_id"):
                evidence = learning.setdefault("cross_channel_evidence", [])
                evidence.append({
                    "transfer_id": transfer.get("transfer_id"),
                    "target_channel": transfer.get("target_channel"),
                    "confirmed": confirmed,
                    "date": datetime.now().isoformat(),
                })

                # Boost confidence slightly if confirmed
                if confirmed:
                    current = learning.get("confidence", 0)
                    learning["confidence"] = min(1.0, current + 0.05)

                break

        with open(PLAYBOOK_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
