"""
SEO channel specialist tool.

Generates SEO copy variants (page titles, meta descriptions, content
briefs, H1/H2 structures) by loading the seo-copy skill, reading
playbook learnings, and calling the LLM.
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

CHANNEL = "seo"
SKILL_NAME = "seo-copy"

SEO_GUIDANCE = """For each SEO variant, produce:
- subject_line: The page title / H1 tag. Max 60 characters for SERP display. Include the primary keyword in the first half.
- meta_description: 150-160 characters. Must include primary keyword naturally and end with a CTA or value hook.
- content: A structured content outline or full section copy with H2 subheadings, keyword placement notes, and internal linking suggestions.
- cta: The on-page call-to-action (e.g. "Download the guide", "Start free trial").
- tone: One of authoritative, conversational, educational, or a custom descriptor.
- notes: What makes this variant different (keyword angle, content structure, intent match).

SEO-specific rules:
- Match search intent (informational, commercial, transactional, navigational).
- Primary keyword in title, H1, first paragraph, and meta description.
- Secondary keywords distributed across H2s and body naturally.
- Write for featured snippet capture: use question-answer format, numbered lists, or definition structures where appropriate.
- Internal linking: suggest 2-3 related pages/topics to link to.

Follow the seo-copy skill formulas for title structures and content patterns."""


@function_tool
def specialist_seo(
    brief: str,
    num_variants: int = 3,
    campaign_id: str = "",
    audience: str = "",
    constraints: str = "",
) -> str:
    """Generate SEO copy variants using the seo-copy skill and playbook learnings.

    Args:
        brief: The creative brief describing what SEO copy is needed.
        num_variants: Number of variants to generate (default 3, max 5).
        campaign_id: Optional campaign ID to save variants to.
        audience: Optional target audience description.
        constraints: Optional additional constraints (e.g. target keywords,
            competitor URLs, word count, content type).

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
        channel_guidance=SEO_GUIDANCE,
    )
    user_prompt = build_specialist_user_prompt(
        brief=brief,
        num_variants=num_variants,
        audience=audience,
        constraints=constraints,
    )

    raw_response = call_specialist_llm(system_prompt, user_prompt)

    if raw_response.startswith("[Error:"):
        return f"SEO specialist failed: {raw_response}"

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
                "subject_line": v.get("subject_line", ""),
                "meta_description": v.get("meta_description", ""),
                "cta": v.get("cta", ""),
                "tone": v.get("tone", ""),
                "notes": v.get("notes", ""),
                "created_at": datetime.now().isoformat(),
                "status": "draft",
                "generated_by": "specialist_seo",
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
        "specialist": "specialist_seo",
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
    lines.append("SEO SPECIALIST -- Generated Variants")
    lines.append("=" * 60)
    lines.append(f"Brief: {brief[:150]}...")
    if campaign_id:
        lines.append(f"Campaign: {campaign_id}")
    lines.append(f"Variants generated: {len(variants)}")
    lines.append("")

    for v in variants:
        lines.append(f"--- {v.get('variant_id', '?')} ---")
        if v.get("subject_line"):
            lines.append(f"  Title/H1: {v['subject_line']}")
        if v.get("meta_description"):
            lines.append(f"  Meta Description: {v['meta_description']}")
        lines.append(f"  Content: {v.get('content', '(empty)')[:400]}")
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
