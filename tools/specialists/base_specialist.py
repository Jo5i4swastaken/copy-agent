"""
Shared base logic for channel specialists.

Provides:
  - Skill file loading (reads SKILL.md for any channel skill)
  - Playbook reading for channel-specific learnings
  - LLM call wrapper (httpx POST to the OpenAI-compatible endpoint from .env)
  - Variant structuring (parses LLM output into save-ready dicts)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths -- resolved relative to this file so imports work from any cwd
# ---------------------------------------------------------------------------
_TOOLS_DIR: Path = Path(__file__).resolve().parent.parent
_AGENT_ROOT: Path = _TOOLS_DIR.parent
_SKILLS_DIR: Path = _AGENT_ROOT / "skills"
_DATA_DIR: Path = _AGENT_ROOT / "data"
_PLAYBOOK_PATH: Path = _DATA_DIR / "playbook.json"

# Load environment variables from the agent root .env
load_dotenv(_AGENT_ROOT / ".env")

# ---------------------------------------------------------------------------
# LLM endpoint configuration
# ---------------------------------------------------------------------------
_OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
_OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
_SPECIALIST_MODEL: str = os.getenv("SPECIALIST_MODEL", "gpt-5.2")
_SPECIALIST_TEMPERATURE: float = float(os.getenv("SPECIALIST_TEMPERATURE", "0.8"))
_SPECIALIST_MAX_TOKENS: int = int(os.getenv("SPECIALIST_MAX_TOKENS", "4096"))

# Timeout for specialist LLM calls (seconds)
_LLM_TIMEOUT: float = 90.0


# ---------------------------------------------------------------------------
# Skill file loading
# ---------------------------------------------------------------------------

def load_skill(skill_name: str) -> str:
    """Load a channel skill's SKILL.md content.

    Args:
        skill_name: The skill directory name (e.g. 'email-copy', 'sms-copy').

    Returns:
        The full text of the skill file, or an error message if not found.
    """
    skill_path = _SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return f"[Skill '{skill_name}' not found at {skill_path}]"
    return skill_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Playbook reading for channel-specific learnings
# ---------------------------------------------------------------------------

def load_playbook_learnings(channel: str) -> list[dict]:
    """Load active playbook learnings for a specific channel.

    Returns learnings sorted by confidence descending. Includes both
    channel-specific learnings and 'general' learnings that apply
    across channels.

    Args:
        channel: The channel to filter for (e.g. 'email', 'sms').

    Returns:
        List of learning dicts.
    """
    if not _PLAYBOOK_PATH.exists():
        return []

    try:
        with open(_PLAYBOOK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    learnings = data.get("learnings", [])
    if not learnings:
        return []

    # Filter to active learnings for this channel or general
    active = [
        entry for entry in learnings
        if (
            isinstance(entry.get("confidence"), (int, float))
            and entry["confidence"] >= 0.2
            and not entry.get("deactivated", False)
            and entry.get("category", "general") in (channel, "general")
        )
    ]

    # Sort by confidence descending
    active.sort(key=lambda e: e.get("confidence", 0), reverse=True)
    return active


def format_learnings_for_prompt(learnings: list[dict], max_items: int = 10) -> str:
    """Format playbook learnings into a prompt-friendly string.

    Args:
        learnings: List of learning dicts from load_playbook_learnings.
        max_items: Maximum number of learnings to include.

    Returns:
        Formatted string for injection into the specialist prompt.
    """
    if not learnings:
        return "No playbook learnings available for this channel yet."

    lines: list[str] = []
    for entry in learnings[:max_items]:
        conf = entry.get("confidence", 0)
        text = entry.get("learning", "")
        times_confirmed = entry.get("times_confirmed", 0)
        label = "HIGH" if conf >= 0.8 else ("MEDIUM" if conf >= 0.5 else "LOW")
        suffix = f" (confirmed {times_confirmed}x)" if times_confirmed > 0 else ""
        lines.append(f"- [{label}] {text}{suffix}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call wrapper
# ---------------------------------------------------------------------------

def call_specialist_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Make a synchronous LLM call to the OpenAI-compatible endpoint.

    Uses httpx to call the same endpoint configured in .env so that all
    specialist calls route through the same provider as the conductor.

    Args:
        system_prompt: The system message for the specialist.
        user_prompt: The user message containing the brief.
        temperature: Override default temperature if provided.
        max_tokens: Override default max_tokens if provided.

    Returns:
        The assistant's response text, or an error message on failure.
    """
    if not _OPENAI_API_KEY:
        return "[Error: OPENAI_API_KEY not set in environment]"

    url = f"{_OPENAI_BASE_URL.rstrip('/')}/chat/completions"

    payload = {
        "model": _SPECIALIST_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature if temperature is not None else _SPECIALIST_TEMPERATURE,
        "max_tokens": max_tokens if max_tokens is not None else _SPECIALIST_MAX_TOKENS,
    }

    headers = {
        "Authorization": f"Bearer {_OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=_LLM_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        return "[Error: Specialist LLM call timed out after {:.0f}s]".format(
            _LLM_TIMEOUT
        )
    except httpx.HTTPStatusError as exc:
        return f"[Error: LLM returned HTTP {exc.response.status_code}: {exc.response.text[:500]}]"
    except Exception as exc:
        return f"[Error: Specialist LLM call failed: {exc}]"


# ---------------------------------------------------------------------------
# Variant structuring
# ---------------------------------------------------------------------------

def parse_variants_from_response(
    raw_response: str,
    channel: str,
    num_variants: int,
) -> list[dict]:
    """Parse the specialist LLM response into structured variant dicts.

    The specialist is prompted to return JSON, but this parser handles
    both clean JSON and freeform text gracefully.

    Args:
        raw_response: The raw text from the LLM.
        channel: The channel (email, sms, seo, ad).
        num_variants: Expected number of variants.

    Returns:
        List of variant dicts ready for save_copy_variant.
    """
    # Attempt 1: Try to parse as a JSON array
    variants = _try_parse_json_variants(raw_response)
    if variants:
        return _normalize_variants(variants, channel)

    # Attempt 2: Try to extract JSON from markdown code blocks
    code_block_match = re.search(
        r"```(?:json)?\s*(\[.*?\])\s*```",
        raw_response,
        re.DOTALL,
    )
    if code_block_match:
        variants = _try_parse_json_variants(code_block_match.group(1))
        if variants:
            return _normalize_variants(variants, channel)

    # Attempt 3: Split by variant markers and build minimal dicts
    return _parse_freeform_variants(raw_response, channel, num_variants)


def _try_parse_json_variants(text: str) -> list[dict] | None:
    """Try to parse text as a JSON array of variant objects."""
    text = text.strip()
    # Find the outermost JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start:end + 1])
        if isinstance(parsed, list) and all(isinstance(v, dict) for v in parsed):
            return parsed
    except json.JSONDecodeError:
        pass
    return None


def _normalize_variants(variants: list[dict], channel: str) -> list[dict]:
    """Ensure each variant dict has the required fields."""
    normalized: list[dict] = []
    for i, v in enumerate(variants):
        normalized.append({
            "variant_id": v.get("variant_id", f"v{i + 1}"),
            "channel": channel,
            "content": v.get("content", v.get("body", v.get("message", ""))),
            "subject_line": v.get("subject_line", v.get("headline", v.get("title", ""))),
            "cta": v.get("cta", v.get("call_to_action", "")),
            "tone": v.get("tone", ""),
            "notes": v.get("notes", v.get("differentiator", "")),
            "meta_description": v.get("meta_description", ""),
            "preheader": v.get("preheader", ""),
        })
    return normalized


def _parse_freeform_variants(
    text: str,
    channel: str,
    num_variants: int,
) -> list[dict]:
    """Parse freeform text with variant markers into structured dicts.

    Looks for patterns like 'Variant 1', 'v1', '## Variant A' etc.
    """
    # Split on common variant delimiters
    parts = re.split(
        r"(?:^|\n)(?:#{1,3}\s*)?(?:Variant\s+(?:v?\d+|[A-Z])|\*\*Variant\s+(?:v?\d+|[A-Z])\*\*)",
        text,
        flags=re.IGNORECASE,
    )

    # First element is usually preamble text, skip if it looks like instructions
    if len(parts) > 1:
        parts = parts[1:]  # Drop preamble

    variants: list[dict] = []
    for i, part in enumerate(parts[:num_variants]):
        part = part.strip()
        if not part:
            continue

        variant: dict = {
            "variant_id": f"v{i + 1}",
            "channel": channel,
            "content": part,
            "subject_line": _extract_field(part, ["subject", "subject_line", "headline", "title"]),
            "cta": _extract_field(part, ["cta", "call to action", "call-to-action"]),
            "tone": _extract_field(part, ["tone"]),
            "notes": "",
            "meta_description": _extract_field(part, ["meta description", "meta_description"]),
            "preheader": _extract_field(part, ["preheader"]),
        }
        variants.append(variant)

    # If no variants were parsed, return the entire response as one variant
    if not variants:
        variants.append({
            "variant_id": "v1",
            "channel": channel,
            "content": text,
            "subject_line": "",
            "cta": "",
            "tone": "",
            "notes": "Raw specialist output -- manual parsing may be needed.",
            "meta_description": "",
            "preheader": "",
        })

    return variants


def _extract_field(text: str, field_names: list[str]) -> str:
    """Extract a labeled field value from freeform text.

    Looks for patterns like 'Subject: ...' or '**CTA:** ...'
    """
    for name in field_names:
        pattern = rf"(?:\*\*)?{re.escape(name)}(?:\*\*)?[\s:]+(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip("*")
    return ""


# ---------------------------------------------------------------------------
# Build specialist system prompt
# ---------------------------------------------------------------------------

def build_specialist_system_prompt(
    channel: str,
    skill_content: str,
    learnings_text: str,
    channel_guidance: str,
) -> str:
    """Assemble the full system prompt for a channel specialist.

    Args:
        channel: The channel name (email, sms, seo, ad).
        skill_content: The loaded SKILL.md content.
        learnings_text: Formatted playbook learnings.
        channel_guidance: Channel-specific generation instructions.

    Returns:
        A complete system prompt string.
    """
    return f"""You are a {channel} copy specialist agent. Your ONLY job is to generate high-quality {channel} copy variants based on the brief you receive.

## Channel Skill Knowledge
{skill_content}

## Playbook Learnings (Apply These)
{learnings_text}

## Output Format
{channel_guidance}

## Rules
1. Generate the exact number of variants requested.
2. Each variant MUST differ on at least one dimension (tone, CTA style, headline approach, length, structure, or personalization level).
3. Return your output as a JSON array of objects. Each object must have these fields:
   - "variant_id": string (e.g. "v1", "v2")
   - "content": string (the main body copy)
   - "subject_line": string (subject line, headline, or title depending on channel)
   - "cta": string (call-to-action text)
   - "tone": string (e.g. "professional", "casual", "urgent")
   - "notes": string (what makes this variant different from the others)
4. Apply playbook learnings marked HIGH with confidence. Treat MEDIUM as strong suggestions. Treat LOW as ideas worth testing.
5. Do NOT include any text outside the JSON array. Return ONLY the JSON array.
"""


# ---------------------------------------------------------------------------
# Build specialist user prompt
# ---------------------------------------------------------------------------

def build_specialist_user_prompt(
    brief: str,
    num_variants: int,
    audience: str = "",
    constraints: str = "",
) -> str:
    """Assemble the user prompt sent to the specialist LLM.

    Args:
        brief: The creative brief.
        num_variants: Number of variants to generate.
        audience: Optional target audience description.
        constraints: Optional additional constraints.

    Returns:
        A user prompt string.
    """
    parts = [f"Brief: {brief}", f"Number of variants: {num_variants}"]

    if audience:
        parts.append(f"Target audience: {audience}")
    if constraints:
        parts.append(f"Constraints: {constraints}")

    parts.append(
        f"\nGenerate exactly {num_variants} copy variants as a JSON array. "
        "Each variant should take a meaningfully different approach."
    )

    return "\n".join(parts)
