"""
Multi-channel orchestration tools for the Copy Agent.

Provides campaign planning across multiple channels, specialist dispatching,
and active test monitoring.
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
CAMPAIGNS_DIR = DATA_DIR / "campaigns"
ORCHESTRATION_DIR = DATA_DIR / "orchestration"

# Channel → specialist tool name mapping
CHANNEL_SPECIALISTS = {
    "email": "specialist_email",
    "sms": "specialist_sms",
    "ad": "specialist_ad",
    "seo": "specialist_seo",
}

VALID_CHANNELS = set(CHANNEL_SPECIALISTS.keys())


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


# ---------------------------------------------------------------------------
# Tool 1: plan_multi_channel_campaign
# ---------------------------------------------------------------------------

@function_tool
def plan_multi_channel_campaign(
    name: str,
    brief: str,
    channels: str,
    audience: str = "",
    constraints: str = "",
) -> str:
    """Plan a campaign that spans multiple channels.

    Creates a campaign directory for each channel with a brief.json and
    empty variants.json, plus an orchestration manifest linking them.

    Args:
        name: Campaign name (used as slug base, e.g. "spring-sale-2026").
        brief: The creative brief shared across all channels.
        channels: Comma-separated channel list (e.g. "email,sms,ad").
        audience: Optional target audience description.
        constraints: Optional constraints (e.g. brand voice, deadlines).

    Returns:
        Summary of created campaign directories and next steps.
    """
    # Parse and validate channels
    channel_list = [c.strip().lower() for c in channels.split(",") if c.strip()]
    invalid = [c for c in channel_list if c not in VALID_CHANNELS]
    if invalid:
        return (
            f"Error: Invalid channels: {', '.join(invalid)}. "
            f"Valid channels: {', '.join(sorted(VALID_CHANNELS))}."
        )

    if not channel_list:
        return "Error: No channels specified. Provide at least one channel."

    if not name.strip():
        return "Error: Campaign name is required."

    now = datetime.now().isoformat()
    campaign_ids = []

    for channel in channel_list:
        campaign_id = f"{name.strip()}-{channel}"
        campaign_dir = CAMPAIGNS_DIR / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)

        # Create brief.json
        brief_data = {
            "campaign_id": campaign_id,
            "name": name.strip(),
            "channel": channel,
            "brief": brief,
            "audience": audience,
            "constraints": constraints,
            "status": "draft",
            "created_at": now,
            "multi_channel_group": name.strip(),
        }
        _save_json(campaign_dir / "brief.json", brief_data)

        # Create empty variants.json
        variants_path = campaign_dir / "variants.json"
        if not variants_path.exists():
            _save_json(variants_path, [])

        campaign_ids.append(campaign_id)

    # Create orchestration manifest
    manifest = {
        "group_id": name.strip(),
        "channels": channel_list,
        "campaign_ids": campaign_ids,
        "brief": brief,
        "audience": audience,
        "constraints": constraints,
        "created_at": now,
        "status": "planned",
    }
    manifest_path = ORCHESTRATION_DIR / "manifests" / f"{name.strip()}.json"
    _save_json(manifest_path, manifest)

    # Format output
    lines = [
        "=" * 60,
        f"MULTI-CHANNEL CAMPAIGN PLANNED: {name}",
        "=" * 60,
        f"Channels: {', '.join(channel_list)}",
        f"Campaigns created: {len(campaign_ids)}",
        "",
    ]
    for cid in campaign_ids:
        lines.append(f"  - {cid}")
    lines.append("")
    lines.append("Next steps:")
    lines.append("  1. Use dispatch_to_specialist for each channel to generate variants.")
    lines.append("  2. Review variants and approve for deployment.")
    lines.append("  3. Use start_ab_test to begin A/B testing on any campaign.")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: dispatch_to_specialist
# ---------------------------------------------------------------------------

@function_tool
def dispatch_to_specialist(
    campaign_id: str,
    channel: str = "",
    num_variants: int = 3,
) -> str:
    """Dispatch copy generation to the appropriate channel specialist.

    Reads the campaign brief and calls the right specialist tool to
    generate variants. This is a routing function -- the actual generation
    happens in the specialist.

    Args:
        campaign_id: The campaign to generate copy for.
        channel: Channel override. If empty, reads from the campaign brief.
        num_variants: Number of variants to generate (default 3).

    Returns:
        The specialist's output or an error message.
    """
    campaign_dir = CAMPAIGNS_DIR / campaign_id
    brief_path = campaign_dir / "brief.json"

    if not brief_path.exists():
        return f"Error: Campaign '{campaign_id}' not found."

    brief_data = _load_json(brief_path) or {}
    resolved_channel = channel.strip().lower() or brief_data.get("channel", "")

    if resolved_channel not in VALID_CHANNELS:
        return (
            f"Error: Unknown channel '{resolved_channel}'. "
            f"Valid: {', '.join(sorted(VALID_CHANNELS))}."
        )

    specialist_name = CHANNEL_SPECIALISTS[resolved_channel]

    # Import and call the specialist dynamically
    try:
        if resolved_channel == "email":
            from tools.specialists.email_specialist import specialist_email
            result = specialist_email(
                brief=brief_data.get("brief", ""),
                num_variants=num_variants,
                campaign_id=campaign_id,
                audience=brief_data.get("audience", ""),
                constraints=brief_data.get("constraints", ""),
            )
        elif resolved_channel == "sms":
            from tools.specialists.sms_specialist import specialist_sms
            result = specialist_sms(
                brief=brief_data.get("brief", ""),
                num_variants=num_variants,
                campaign_id=campaign_id,
                audience=brief_data.get("audience", ""),
                constraints=brief_data.get("constraints", ""),
            )
        elif resolved_channel == "ad":
            from tools.specialists.ad_specialist import specialist_ad
            result = specialist_ad(
                brief=brief_data.get("brief", ""),
                num_variants=num_variants,
                campaign_id=campaign_id,
                audience=brief_data.get("audience", ""),
                constraints=brief_data.get("constraints", ""),
            )
        elif resolved_channel == "seo":
            from tools.specialists.seo_specialist import specialist_seo
            result = specialist_seo(
                brief=brief_data.get("brief", ""),
                num_variants=num_variants,
                campaign_id=campaign_id,
                audience=brief_data.get("audience", ""),
                constraints=brief_data.get("constraints", ""),
            )
        else:
            return f"Error: No specialist found for channel '{resolved_channel}'."
    except Exception as exc:
        return f"Error: Specialist '{specialist_name}' failed: {exc}"

    # Log the dispatch
    _log_dispatch(campaign_id, resolved_channel, specialist_name)

    return result


def _log_dispatch(campaign_id: str, channel: str, specialist: str) -> None:
    log_path = ORCHESTRATION_DIR / "dispatch_log.json"
    lock_path = log_path.with_suffix(log_path.suffix + ".lock")
    entry = {
        "campaign_id": campaign_id,
        "channel": channel,
        "specialist": specialist,
        "timestamp": datetime.now().isoformat(),
    }
    with FileLock(str(lock_path)):
        ORCHESTRATION_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except (json.JSONDecodeError, OSError, FileNotFoundError):
            log = []
        log.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 3: list_active_tests
# ---------------------------------------------------------------------------

@function_tool
def list_active_tests() -> str:
    """List all A/B tests currently in COLLECTING, WAITING, or ANALYZING state.

    Returns a formatted summary of each active test with its campaign,
    hypothesis, current metrics snapshot, and next check time.
    """
    if not CAMPAIGNS_DIR.exists():
        return "No campaigns found."

    active: list[dict] = []

    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue
        state_path = campaign_dir / "ab_test_state.json"
        if not state_path.exists():
            continue
        state = _load_json(state_path)
        if state is None:
            continue
        if state.get("state") in ("COLLECTING", "WAITING", "ANALYZING"):
            active.append(state)

    if not active:
        return "No active A/B tests."

    lines = [
        "=" * 60,
        f"ACTIVE A/B TESTS ({len(active)})",
        "=" * 60,
        "",
    ]

    for t in active:
        lines.append(f"Test: {t.get('test_id', '?')}")
        lines.append(f"  Campaign: {t.get('campaign_id', '?')}")
        lines.append(f"  State: {t.get('state', '?')}")
        lines.append(f"  Hypothesis: {t.get('hypothesis', 'N/A')}")
        lines.append(f"  Next check: {t.get('next_check_at', 'N/A')}")

        metrics = t.get("current_metrics", {})
        if metrics:
            lines.append("  Current metrics:")
            for variant_id, m in metrics.items():
                sample = m.get("sample_size", "?")
                lines.append(f"    {variant_id}: sample={sample}, {m}")

        checks = t.get("checks_performed", [])
        if checks:
            last = checks[-1]
            lines.append(f"  Last check: {last.get('checked_at', '?')} → {last.get('verdict', '?')}")

        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
