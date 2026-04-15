"""
Tests for tools/specialists/base_specialist.py — shared specialist logic.

Tests parse_variants_from_response (JSON, markdown, freeform), load_skill,
load_playbook_learnings, format_learnings_for_prompt, and prompt builders.
LLM calls are NOT tested here (would need httpx mocking).
"""

import json

import pytest

from tools.specialists.base_specialist import (
    build_specialist_system_prompt,
    build_specialist_user_prompt,
    format_learnings_for_prompt,
    load_playbook_learnings,
    load_skill,
    parse_variants_from_response,
)
import tools.specialists.base_specialist as bs


@pytest.fixture(autouse=True)
def patch_specialist_paths(tmp_path, monkeypatch):
    """Redirect specialist paths to tmp_path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    monkeypatch.setattr(bs, "_AGENT_ROOT", tmp_path)
    monkeypatch.setattr(bs, "_SKILLS_DIR", skills_dir)
    monkeypatch.setattr(bs, "_DATA_DIR", data_dir)
    monkeypatch.setattr(bs, "_PLAYBOOK_PATH", data_dir / "playbook.json")

    return tmp_path


# =========================================================================
# parse_variants_from_response
# =========================================================================

class TestParseVariantsFromResponse:
    def test_parses_clean_json_array(self):
        response = json.dumps([
            {"variant_id": "v1", "content": "Body 1", "subject_line": "Subject 1", "cta": "Buy Now", "tone": "urgent"},
            {"variant_id": "v2", "content": "Body 2", "subject_line": "Subject 2", "cta": "Learn More", "tone": "casual"},
        ])
        variants = parse_variants_from_response(response, "email", 2)
        assert len(variants) == 2
        assert variants[0]["variant_id"] == "v1"
        assert variants[0]["content"] == "Body 1"
        assert variants[0]["channel"] == "email"

    def test_parses_json_in_code_block(self):
        response = """Here are the variants:

```json
[
  {"variant_id": "v1", "content": "Hello there", "subject_line": "Greetings", "cta": "Click", "tone": "friendly"},
  {"variant_id": "v2", "content": "Hi friend", "subject_line": "Hey!", "cta": "Tap", "tone": "playful"}
]
```

Let me know if you need changes!"""
        variants = parse_variants_from_response(response, "sms", 2)
        assert len(variants) == 2
        assert variants[0]["content"] == "Hello there"
        assert variants[1]["channel"] == "sms"

    def test_parses_freeform_variant_markers(self):
        response = """
Variant 1
Subject: Spring Sale Alert
Body: Don't miss 30% off everything this spring!
CTA: Shop Now
Tone: urgent

Variant 2
Subject: Fresh Deals Ahead
Body: Spring is here and so are our best deals.
CTA: Browse Deals
Tone: playful
"""
        variants = parse_variants_from_response(response, "email", 2)
        assert len(variants) >= 1
        # At minimum, should extract some content
        assert variants[0]["content"] != ""

    def test_fallback_to_single_variant(self):
        """Unparseable text should return the whole thing as a single variant."""
        response = "Just some random copy text with no structure at all."
        variants = parse_variants_from_response(response, "ad", 3)
        assert len(variants) >= 1
        assert variants[0]["channel"] == "ad"
        assert "random copy text" in variants[0]["content"]

    def test_normalizes_field_names(self):
        """Alternative field names (body, headline, call_to_action) should be mapped."""
        response = json.dumps([
            {"body": "Email body", "headline": "Big Sale", "call_to_action": "Shop", "tone": "bold"},
        ])
        variants = parse_variants_from_response(response, "email", 1)
        assert variants[0]["content"] == "Email body"
        assert variants[0]["subject_line"] == "Big Sale"
        assert variants[0]["cta"] == "Shop"

    def test_auto_assigns_variant_ids(self):
        """If variant_id is missing, auto-assigns v1, v2, etc."""
        response = json.dumps([
            {"content": "A"},
            {"content": "B"},
        ])
        variants = parse_variants_from_response(response, "sms", 2)
        assert variants[0]["variant_id"] == "v1"
        assert variants[1]["variant_id"] == "v2"


# =========================================================================
# load_skill
# =========================================================================

class TestLoadSkill:
    def test_loads_existing_skill(self, patch_specialist_paths):
        skill_dir = patch_specialist_paths / "skills" / "email-copy"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Email Copy Skill\nBe persuasive.")

        result = load_skill("email-copy")
        assert "Email Copy Skill" in result
        assert "Be persuasive" in result

    def test_missing_skill_returns_message(self, patch_specialist_paths):
        result = load_skill("nonexistent-skill")
        assert "not found" in result.lower()


# =========================================================================
# load_playbook_learnings
# =========================================================================

class TestLoadPlaybookLearnings:
    def test_loads_channel_learnings(self, patch_specialist_paths):
        playbook = {
            "learnings": [
                {"category": "email", "learning": "Email tip", "confidence": 0.8},
                {"category": "sms", "learning": "SMS tip", "confidence": 0.7},
                {"category": "general", "learning": "General tip", "confidence": 0.5},
            ]
        }
        (patch_specialist_paths / "data" / "playbook.json").write_text(json.dumps(playbook))

        result = load_playbook_learnings("email")
        categories = [l["category"] for l in result]
        assert "email" in categories
        assert "general" in categories
        assert "sms" not in categories

    def test_excludes_low_confidence(self, patch_specialist_paths):
        playbook = {
            "learnings": [
                {"category": "email", "learning": "Good", "confidence": 0.5},
                {"category": "email", "learning": "Too low", "confidence": 0.1},
            ]
        }
        (patch_specialist_paths / "data" / "playbook.json").write_text(json.dumps(playbook))

        result = load_playbook_learnings("email")
        texts = [l["learning"] for l in result]
        assert "Good" in texts
        assert "Too low" not in texts

    def test_excludes_deactivated(self, patch_specialist_paths):
        playbook = {
            "learnings": [
                {"category": "email", "learning": "Active", "confidence": 0.8, "deactivated": False},
                {"category": "email", "learning": "Deactivated", "confidence": 0.8, "deactivated": True},
            ]
        }
        (patch_specialist_paths / "data" / "playbook.json").write_text(json.dumps(playbook))

        result = load_playbook_learnings("email")
        texts = [l["learning"] for l in result]
        assert "Active" in texts
        assert "Deactivated" not in texts

    def test_sorted_by_confidence_descending(self, patch_specialist_paths):
        playbook = {
            "learnings": [
                {"category": "email", "learning": "Low", "confidence": 0.3},
                {"category": "email", "learning": "High", "confidence": 0.9},
                {"category": "email", "learning": "Mid", "confidence": 0.6},
            ]
        }
        (patch_specialist_paths / "data" / "playbook.json").write_text(json.dumps(playbook))

        result = load_playbook_learnings("email")
        confidences = [l["confidence"] for l in result]
        assert confidences == sorted(confidences, reverse=True)

    def test_no_playbook_returns_empty(self, patch_specialist_paths):
        result = load_playbook_learnings("email")
        assert result == []


# =========================================================================
# format_learnings_for_prompt
# =========================================================================

class TestFormatLearningsForPrompt:
    def test_formats_learnings(self):
        learnings = [
            {"learning": "Use numbers in subject lines", "confidence": 0.9, "times_confirmed": 3},
            {"learning": "Keep CTAs short", "confidence": 0.5, "times_confirmed": 1},
        ]
        result = format_learnings_for_prompt(learnings)
        assert "[HIGH]" in result
        assert "[MEDIUM]" in result
        assert "confirmed 3x" in result

    def test_empty_learnings(self):
        result = format_learnings_for_prompt([])
        assert "no playbook" in result.lower()

    def test_truncates_to_max(self):
        learnings = [
            {"learning": f"Tip {i}", "confidence": 0.5}
            for i in range(20)
        ]
        result = format_learnings_for_prompt(learnings, max_items=5)
        assert result.count("- [") == 5


# =========================================================================
# build_specialist_system_prompt
# =========================================================================

class TestBuildSpecialistSystemPrompt:
    def test_includes_all_sections(self):
        result = build_specialist_system_prompt(
            channel="email",
            skill_content="# Email Skills",
            learnings_text="- [HIGH] Use emojis",
            channel_guidance="Include subject_line and body.",
        )
        assert "email" in result.lower()
        assert "Email Skills" in result
        assert "Use emojis" in result
        assert "subject_line" in result


# =========================================================================
# build_specialist_user_prompt
# =========================================================================

class TestBuildSpecialistUserPrompt:
    def test_includes_brief_and_variants(self):
        result = build_specialist_user_prompt(
            brief="Write copy for our spring sale",
            num_variants=3,
        )
        assert "spring sale" in result
        assert "3" in result

    def test_includes_audience_and_constraints(self):
        result = build_specialist_user_prompt(
            brief="Brief",
            num_variants=2,
            audience="Young professionals",
            constraints="No slang",
        )
        assert "Young professionals" in result
        assert "No slang" in result

    def test_omits_empty_optional_fields(self):
        result = build_specialist_user_prompt(brief="Brief", num_variants=1)
        assert "audience" not in result.lower()
        assert "constraints" not in result.lower()
