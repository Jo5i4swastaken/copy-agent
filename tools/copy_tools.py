"""
Custom tools for the Copy Agent — campaign creation, variant storage,
and campaign management.

All data is persisted as JSON files under data/campaigns/{campaign_id}/.
Thread safety on writes is provided by filelock.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from filelock import FileLock
from omniagents import function_tool

# ---------------------------------------------------------------------------
# Paths — DATA_DIR is always <agent-root>/data
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
CAMPAIGNS_DIR: Path = DATA_DIR / "campaigns"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Lowercase, replace spaces/underscores with hyphens, strip everything
    that is not alphanumeric or a hyphen, then collapse repeated hyphens."""
    slug = text.lower().strip()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug


def _campaign_dir(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / campaign_id


def _read_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict | list) -> None:
    """Write JSON atomically using a .lock file next to the target."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


VALID_CHANNELS = {"email", "sms", "seo", "ad"}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@function_tool
def generate_copy(
    brief: str,
    channel: str,
    num_variants: int = 3,
    campaign_name: str = "",
) -> str:
    """Create a new campaign and return a structured prompt telling the agent
    what copy to generate.

    Args:
        brief: The creative brief describing what copy is needed.
        channel: Target channel — must be one of: email, sms, seo, ad.
        num_variants: Number of copy variants to generate (default 3).
        campaign_name: Optional human-readable campaign name. If omitted an
            auto-generated ID based on the current timestamp will be used.

    This tool does NOT generate copy itself. It sets up the campaign folder,
    saves the brief, and returns instructions that tell the model what to
    produce next."""

    # Validate channel
    channel = channel.strip().lower()
    if channel not in VALID_CHANNELS:
        return (
            f"Error: Invalid channel '{channel}'. "
            f"Must be one of: {', '.join(sorted(VALID_CHANNELS))}."
        )

    # Derive campaign_id
    if campaign_name.strip():
        campaign_id = _slugify(campaign_name)
        if not campaign_id:
            campaign_id = datetime.now().strftime("campaign-%Y%m%d-%H%M%S")
    else:
        campaign_id = datetime.now().strftime("campaign-%Y%m%d-%H%M%S")

    # Ensure uniqueness — append a numeric suffix if the directory exists
    base_id = campaign_id
    counter = 1
    while _campaign_dir(campaign_id).exists():
        counter += 1
        campaign_id = f"{base_id}-{counter}"

    # Create campaign directory
    campaign_path = _campaign_dir(campaign_id)
    campaign_path.mkdir(parents=True, exist_ok=True)

    # Save brief.json
    brief_data = {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name.strip() or campaign_id,
        "brief": brief,
        "channel": channel,
        "num_variants": num_variants,
        "created_at": datetime.now().isoformat(),
        "status": "draft",
    }
    _write_json(campaign_path / "brief.json", brief_data)

    # Initialize empty variants.json
    _write_json(campaign_path / "variants.json", [])

    # Build channel-specific guidance for the model
    channel_guidance = {
        "email": (
            "For each variant, provide: subject_line, body content, "
            "CTA (call-to-action), and tone."
        ),
        "sms": (
            "For each variant, provide: message text (max 160 chars recommended), "
            "CTA, and tone. Keep it concise and action-oriented."
        ),
        "seo": (
            "For each variant, provide: meta title (~60 chars), "
            "meta description (~155 chars), primary keyword focus, "
            "body content, and tone."
        ),
        "ad": (
            "For each variant, provide: headline, body copy, "
            "CTA, display URL (if applicable), and tone."
        ),
    }

    guidance = channel_guidance[channel]

    return (
        f"Campaign '{campaign_id}' created successfully.\n\n"
        f"Brief: {brief}\n"
        f"Channel: {channel}\n"
        f"Variants requested: {num_variants}\n\n"
        f"Now generate {num_variants} {channel} copy variants.\n"
        f"{guidance}\n\n"
        f"After generating each variant, call save_copy_variant with "
        f"campaign_id='{campaign_id}' to store it. "
        f"Use variant IDs like 'v1', 'v2', 'v3', etc."
    )


@function_tool
def save_copy_variant(
    campaign_id: str,
    variant_id: str,
    channel: str,
    content: str,
    subject_line: str = "",
    cta: str = "",
    tone: str = "",
    notes: str = "",
) -> str:
    """Save a single copy variant to an existing campaign.

    Args:
        campaign_id: The campaign to add the variant to.
        variant_id: A short identifier for this variant (e.g. 'v1', 'v2').
        channel: The channel this variant targets (email, sms, seo, ad).
        content: The main copy content / body text of the variant.
        subject_line: Subject line (primarily for email variants).
        cta: Call-to-action text.
        tone: Tone descriptor (e.g. 'professional', 'playful', 'urgent').
        notes: Any additional notes or context about this variant.

    Returns a confirmation message with the saved variant details."""

    campaign_path = _campaign_dir(campaign_id)
    variants_path = campaign_path / "variants.json"
    brief_path = campaign_path / "brief.json"

    # Validate campaign exists
    if not brief_path.exists():
        return f"Error: Campaign '{campaign_id}' not found. Run generate_copy first."

    if not variants_path.exists():
        return (
            f"Error: variants.json missing for campaign '{campaign_id}'. "
            "The campaign may be corrupted."
        )

    # Validate channel
    channel = channel.strip().lower()
    if channel not in VALID_CHANNELS:
        return (
            f"Error: Invalid channel '{channel}'. "
            f"Must be one of: {', '.join(sorted(VALID_CHANNELS))}."
        )

    # Build variant record
    variant = {
        "variant_id": variant_id.strip(),
        "channel": channel,
        "content": content,
        "subject_line": subject_line,
        "cta": cta,
        "tone": tone,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "status": "draft",
    }

    # Append to variants.json with file lock
    lock_path = variants_path.with_suffix(variants_path.suffix + ".lock")
    with FileLock(str(lock_path)):
        variants: list = _read_json(variants_path)
        variants.append(variant)
        with open(variants_path, "w", encoding="utf-8") as f:
            json.dump(variants, f, indent=2, ensure_ascii=False)

    return (
        f"Variant '{variant_id}' saved to campaign '{campaign_id}'.\n"
        f"Channel: {channel} | Tone: {tone or 'not specified'} | "
        f"Status: draft\n"
        f"Total variants in campaign: {len(variants)}"
    )


@function_tool
def list_campaigns(
    status: str = "all",
    channel: str = "all",
    limit: int = 10,
) -> str:
    """List existing campaigns with summary metadata.

    Args:
        status: Filter by campaign status (e.g. 'draft', 'active', 'complete').
            Use 'all' to show every status.
        channel: Filter by channel (email, sms, seo, ad). Use 'all' for no filter.
        limit: Maximum number of campaigns to return (default 10).

    Returns a formatted list of campaigns sorted by creation date (newest first)."""

    if not CAMPAIGNS_DIR.exists():
        return "No campaigns found. Use generate_copy to create your first campaign."

    campaigns = []
    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue
        brief_path = campaign_dir / "brief.json"
        if not brief_path.exists():
            continue

        try:
            brief = _read_json(brief_path)
        except (json.JSONDecodeError, OSError):
            continue

        # Apply filters
        if status.lower() != "all" and brief.get("status", "").lower() != status.lower():
            continue
        if channel.lower() != "all" and brief.get("channel", "").lower() != channel.lower():
            continue

        # Count variants
        variants_path = campaign_dir / "variants.json"
        num_variants = 0
        if variants_path.exists():
            try:
                variants = _read_json(variants_path)
                num_variants = len(variants)
            except (json.JSONDecodeError, OSError):
                pass

        campaigns.append({
            "campaign_id": brief.get("campaign_id", campaign_dir.name),
            "campaign_name": brief.get("campaign_name", ""),
            "channel": brief.get("channel", "unknown"),
            "status": brief.get("status", "unknown"),
            "created_at": brief.get("created_at", ""),
            "num_variants": num_variants,
        })

    if not campaigns:
        filter_msg = ""
        if status.lower() != "all":
            filter_msg += f" with status='{status}'"
        if channel.lower() != "all":
            filter_msg += f" on channel='{channel}'"
        return f"No campaigns found{filter_msg}."

    # Sort by created_at descending
    campaigns.sort(key=lambda c: c["created_at"], reverse=True)

    # Apply limit
    campaigns = campaigns[:limit]

    # Format output
    lines = [f"Found {len(campaigns)} campaign(s):\n"]
    for i, c in enumerate(campaigns, 1):
        lines.append(
            f"{i}. {c['campaign_id']}\n"
            f"   Name: {c['campaign_name']}\n"
            f"   Channel: {c['channel']} | Status: {c['status']}\n"
            f"   Variants: {c['num_variants']} | Created: {c['created_at']}"
        )

    return "\n".join(lines)


@function_tool
def get_campaign(campaign_id: str) -> str:
    """Retrieve full details for a specific campaign including its brief,
    all variants, and metrics summary if available.

    Args:
        campaign_id: The ID of the campaign to retrieve.

    Returns formatted campaign details with brief, variants, and any metrics."""

    campaign_path = _campaign_dir(campaign_id)
    brief_path = campaign_path / "brief.json"

    if not brief_path.exists():
        return f"Error: Campaign '{campaign_id}' not found."

    try:
        brief = _read_json(brief_path)
    except (json.JSONDecodeError, OSError) as exc:
        return f"Error reading campaign brief: {exc}"

    # Build header
    lines = [
        f"Campaign: {brief.get('campaign_id', campaign_id)}",
        f"Name: {brief.get('campaign_name', '')}",
        f"Channel: {brief.get('channel', 'unknown')}",
        f"Status: {brief.get('status', 'unknown')}",
        f"Created: {brief.get('created_at', '')}",
        f"Variants requested: {brief.get('num_variants', 'N/A')}",
        "",
        "--- Brief ---",
        brief.get("brief", "(no brief text)"),
    ]

    # Variants
    variants_path = campaign_path / "variants.json"
    if variants_path.exists():
        try:
            variants = _read_json(variants_path)
        except (json.JSONDecodeError, OSError):
            variants = []

        lines.append("")
        lines.append(f"--- Variants ({len(variants)}) ---")

        if not variants:
            lines.append("No variants saved yet.")
        else:
            for v in variants:
                lines.append("")
                lines.append(f"[{v.get('variant_id', '?')}] ({v.get('status', 'draft')})")
                if v.get("subject_line"):
                    lines.append(f"  Subject: {v['subject_line']}")
                lines.append(f"  Content: {v.get('content', '(empty)')}")
                if v.get("cta"):
                    lines.append(f"  CTA: {v['cta']}")
                if v.get("tone"):
                    lines.append(f"  Tone: {v['tone']}")
                if v.get("notes"):
                    lines.append(f"  Notes: {v['notes']}")
                lines.append(f"  Created: {v.get('created_at', '')}")
    else:
        lines.append("\n(No variants file found.)")

    # Metrics summary (optional — only if metrics.json exists)
    metrics_path = campaign_path / "metrics.json"
    if metrics_path.exists():
        try:
            metrics = _read_json(metrics_path)
            lines.append("")
            lines.append("--- Metrics Summary ---")
            if isinstance(metrics, list) and metrics:
                # Group by variant for a compact summary
                by_variant: dict[str, list[str]] = {}
                for m in metrics:
                    vid = m.get("variant_id", "?")
                    by_variant.setdefault(vid, []).append(
                        f"{m.get('metric_type', '?')}={m.get('value', 'N/A')}"
                    )
                for vid, metric_strs in sorted(by_variant.items()):
                    lines.append(f"  [{vid}] {', '.join(metric_strs)}")
            elif isinstance(metrics, dict):
                for key, val in metrics.items():
                    lines.append(f"  {key}: {val}")
            else:
                lines.append("  No metric entries recorded yet.")
        except (json.JSONDecodeError, OSError):
            lines.append("\n(Metrics file exists but could not be read.)")

    return "\n".join(lines)
