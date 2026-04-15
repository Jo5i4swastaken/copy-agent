"""
Email channel specialist tool.

Generates email copy variants by loading the email-copy skill, reading
playbook learnings for the email channel, and calling the LLM to produce
structured output. Returns a formatted string with all generated variants.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from filelock import FileLock
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

CHANNEL = "email"
SKILL_NAME = "email-copy"

# Channel-specific guidance injected into the specialist system prompt
EMAIL_GUIDANCE = """For each email variant, produce:
- subject_line: Under 50 characters. Front-load the most important words in the first 30 characters for mobile.
- preheader: 40-90 characters. Complements the subject line, does NOT repeat it.
- content: The email body. Use short paragraphs (1-3 sentences), bold key phrases for scanners, and a clear inverted-pyramid structure (hook, value, CTA).
- cta: 2-5 words, action-oriented, first-person when possible (e.g. "Get My Free Report").
- tone: One of professional, casual, urgent, empathetic, playful, or a custom descriptor.
- notes: What makes this variant different (the key dimension varied).

Follow the email-copy skill formulas for subject lines, preheaders, body structure, and CTAs."""


@function_tool
def specialist_email(
    brief: str,
    num_variants: int = 3,
    campaign_id: str = "",
    audience: str = "",
    constraints: str = "",
) -> str:
    """Generate email copy variants using the email-copy skill and playbook learnings.

    This specialist loads channel expertise from the email-copy skill, reads
    accumulated email learnings from the playbook, and generates structured
    variants with subject lines, preheaders, body content, and CTAs.

    Args:
        brief: The creative brief describing what email copy is needed.
        num_variants: Number of variants to generate (default 3, max 5).
        campaign_id: Optional campaign ID to save variants to. If provided,
            variants are automatically saved to the campaign directory.
        audience: Optional target audience description for more targeted copy.
        constraints: Optional additional constraints (e.g. character limits,
            required keywords, brand voice notes).

    Returns:
        Formatted string with all generated variants and their metadata.
    """
    num_variants = max(1, min(num_variants, 5))

    # 1. Load the email-copy skill
    skill_content = load_skill(SKILL_NAME)

    # 2. Read playbook learnings for email
    learnings = load_playbook_learnings(CHANNEL)
    learnings_text = format_learnings_for_prompt(learnings)

    # 3. Build prompts
    system_prompt = build_specialist_system_prompt(
        channel=CHANNEL,
        skill_content=skill_content,
        learnings_text=learnings_text,
        channel_guidance=EMAIL_GUIDANCE,
    )
    user_prompt = build_specialist_user_prompt(
        brief=brief,
        num_variants=num_variants,
        audience=audience,
        constraints=constraints,
    )

    # 4. Call the LLM
    raw_response = call_specialist_llm(system_prompt, user_prompt)

    if raw_response.startswith("[Error:"):
        return f"Email specialist failed: {raw_response}"

    # 5. Parse into structured variants
    variants = parse_variants_from_response(raw_response, CHANNEL, num_variants)

    # 6. Optionally save to campaign
    if campaign_id:
        _save_variants_to_campaign(campaign_id, variants)

    # 7. Log the specialist invocation
    _log_specialist_call(campaign_id, brief, num_variants, len(variants))

    # 8. Format output for the conductor
    return _format_output(variants, campaign_id, brief)


def _save_variants_to_campaign(campaign_id: str, variants: list[dict]) -> None:
    """Append generated variants to a campaign's variants.json."""
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
                "subject_line": v.get("subject_line", ""),
                "cta": v.get("cta", ""),
                "tone": v.get("tone", ""),
                "notes": v.get("notes", ""),
                "created_at": datetime.now().isoformat(),
                "status": "draft",
                "generated_by": "specialist_email",
            }
            existing.append(record)

        with open(variants_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)


def _log_specialist_call(
    campaign_id: str,
    brief: str,
    requested: int,
    generated: int,
) -> None:
    """Append an entry to data/orchestration/specialist_log.json."""
    log_dir = DATA_DIR / "orchestration"
    log_path = log_dir / "specialist_log.json"
    lock_path = log_path.with_suffix(log_path.suffix + ".lock")

    entry = {
        "specialist": "specialist_email",
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
    """Format variants into a readable string for the conductor."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("EMAIL SPECIALIST -- Generated Variants")
    lines.append("=" * 60)
    lines.append(f"Brief: {brief[:150]}...")
    if campaign_id:
        lines.append(f"Campaign: {campaign_id}")
    lines.append(f"Variants generated: {len(variants)}")
    lines.append("")

    for v in variants:
        lines.append(f"--- {v.get('variant_id', '?')} ---")
        if v.get("subject_line"):
            lines.append(f"  Subject: {v['subject_line']}")
        if v.get("preheader"):
            lines.append(f"  Preheader: {v['preheader']}")
        lines.append(f"  Content: {v.get('content', '(empty)')[:300]}")
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
