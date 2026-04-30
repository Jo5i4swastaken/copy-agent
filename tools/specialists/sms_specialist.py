"""
SMS channel specialist tool.

Generates SMS copy variants by loading the sms-copy skill, reading
playbook learnings for the SMS channel, and calling the LLM to produce
structured output.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from tools.lock import FileLock
from omniagents import function_tool

from tools.specialists.base_specialist import (
    build_specialist_system_prompt,
    build_specialist_user_prompt,
    call_specialist_llm,
    format_learnings_for_prompt,
    load_playbook_learnings,
    load_skill,
    parse_variants_from_response,
)

DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data"
CAMPAIGNS_DIR: Path = DATA_DIR / "campaigns"

CHANNEL = "sms"
SKILL_NAME = "sms-copy"

SMS_GUIDANCE = """For each SMS variant, produce:
- content: The full SMS message. MUST be under 160 characters for single-segment delivery. If multi-segment is allowed, stay under 320 characters.
- cta: 2-4 words with a clear action (e.g. "Reply YES", "Tap to shop", "Use code SPRING").
- tone: One of casual, urgent, friendly, exclusive, or a custom descriptor.
- notes: What makes this variant different (the key dimension varied).

SMS-specific rules:
- Front-load the value proposition in the first 40 characters (preview window).
- Include a clear opt-out mention if required by compliance (e.g. "Reply STOP to unsub").
- Use urgency sparingly -- SMS is inherently interruptive, so over-urgency backfires.
- Personalization tokens (e.g. {{first_name}}) count toward character limits.

Follow the sms-copy skill formulas for message structure and CTAs."""


@function_tool
def specialist_sms(
    brief: str,
    num_variants: int = 3,
    campaign_id: str = "",
    audience: str = "",
    constraints: str = "",
) -> str:
    """Generate SMS copy variants using the sms-copy skill and playbook learnings.

    Args:
        brief: The creative brief describing what SMS copy is needed.
        num_variants: Number of variants to generate (default 3, max 5).
        campaign_id: Optional campaign ID to save variants to.
        audience: Optional target audience description.
        constraints: Optional additional constraints (e.g. character limits,
            compliance requirements, personalization tokens).

    Returns:
        Formatted string with all generated variants and their metadata.
    """
    num_variants = max(1, min(num_variants, 5))

    skill_content = load_skill(SKILL_NAME)
    learnings = load_playbook_learnings(CHANNEL)
    learnings_text = format_learnings_for_prompt(learnings)

    system_prompt = build_specialist_system_prompt(
        channel=CHANNEL,
        skill_content=skill_content,
        learnings_text=learnings_text,
        channel_guidance=SMS_GUIDANCE,
    )
    user_prompt = build_specialist_user_prompt(
        brief=brief,
        num_variants=num_variants,
        audience=audience,
        constraints=constraints,
    )

    raw_response = call_specialist_llm(system_prompt, user_prompt)

    if raw_response.startswith("[Error:"):
        return f"SMS specialist failed: {raw_response}"

    variants = parse_variants_from_response(raw_response, CHANNEL, num_variants)

    if campaign_id:
        _save_variants_to_campaign(campaign_id, variants)

    _log_specialist_call(campaign_id, brief, num_variants, len(variants))

    return _format_output(variants, campaign_id, brief)


def _save_variants_to_campaign(campaign_id: str, variants: list[dict]) -> None:
    campaign_path = CAMPAIGNS_DIR / campaign_id
    variants_path = campaign_path / "variants.json"

    if not variants_path.exists():
        return

    lock_path = variants_path.with_suffix(variants_path.suffix + ".lock")
    with FileLock(str(lock_path)):
        try:
            with open(variants_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []

        for v in variants:
            record = {
                "variant_id": v.get("variant_id", ""),
                "channel": CHANNEL,
                "content": v.get("content", ""),
                "cta": v.get("cta", ""),
                "tone": v.get("tone", ""),
                "notes": v.get("notes", ""),
                "created_at": datetime.now().isoformat(),
                "status": "draft",
                "generated_by": "specialist_sms",
            }
            existing.append(record)

        with open(variants_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)


def _log_specialist_call(
    campaign_id: str, brief: str, requested: int, generated: int
) -> None:
    log_dir = DATA_DIR / "orchestration"
    log_path = log_dir / "specialist_log.json"
    lock_path = log_path.with_suffix(log_path.suffix + ".lock")

    entry = {
        "specialist": "specialist_sms",
        "channel": CHANNEL,
        "campaign_id": campaign_id or None,
        "brief_snippet": brief[:200],
        "variants_requested": requested,
        "variants_generated": generated,
        "timestamp": datetime.now().isoformat(),
    }

    with FileLock(str(lock_path)):
        log_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except (json.JSONDecodeError, OSError, FileNotFoundError):
            log_data = []
        log_data.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)


def _format_output(variants: list[dict], campaign_id: str, brief: str) -> str:
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SMS SPECIALIST -- Generated Variants")
    lines.append("=" * 60)
    lines.append(f"Brief: {brief[:150]}...")
    if campaign_id:
        lines.append(f"Campaign: {campaign_id}")
    lines.append(f"Variants generated: {len(variants)}")
    lines.append("")

    for v in variants:
        lines.append(f"--- {v.get('variant_id', '?')} ---")
        char_count = len(v.get("content", ""))
        lines.append(f"  Message ({char_count} chars): {v.get('content', '(empty)')}")
        if v.get("cta"):
            lines.append(f"  CTA: {v['cta']}")
        if v.get("tone"):
            lines.append(f"  Tone: {v['tone']}")
        if v.get("notes"):
            lines.append(f"  Differentiator: {v['notes']}")
        lines.append("")

    if campaign_id:
        lines.append(
            f"Variants saved to campaign '{campaign_id}'. "
            "Use get_campaign to review or log_metrics to track performance."
        )
    lines.append("=" * 60)

    return "\n".join(lines)
