"""
Context factory for the Copy Agent.

Injects dynamic data into the system prompt via Jinja2 template variables:
  - available_skills_block: XML listing skills the agent can activate
  - playbook_summary: formatted learnings from the playbook, grouped by category
  - recent_performance: snapshot of the most recent campaigns
"""

import json
from collections import defaultdict
from pathlib import Path

from omniagents.core.context.decorator import context_factory
from omniagents.core.skills import build_available_skills_block

# ---------------------------------------------------------------------------
# Paths -- resolved relative to this file so the factory works regardless
# of the working directory.
# ---------------------------------------------------------------------------
_THIS_DIR: Path = Path(__file__).resolve().parent
_SKILLS_DIR: Path = _THIS_DIR / "skills"
_DATA_DIR: Path = _THIS_DIR / "data"
_PLAYBOOK_PATH: Path = _DATA_DIR / "playbook.json"
_CAMPAIGNS_DIR: Path = _DATA_DIR / "campaigns"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_CONFIDENCE: float = 0.2
_MAX_LEARNINGS: int = 20
_MAX_RECENT_CAMPAIGNS: int = 5
_ORCHESTRATION_DIR: Path = _DATA_DIR / "orchestration"
_REPORTS_DIR: Path = _DATA_DIR / "reports"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Read and parse a JSON file. Returns None on any failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _confidence_label(confidence: float) -> str:
    """Human-readable confidence bucket."""
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.5:
        return "medium"
    return "low"


def _format_learning(learning: dict) -> str:
    """Format a single learning as a bullet line."""
    conf = learning.get("confidence", 0)
    text = learning.get("learning", "(no text)")
    times_confirmed = learning.get("times_confirmed", 0)
    source = learning.get("source", "")

    suffix = ""
    if times_confirmed > 0:
        suffix = f" (confirmed {times_confirmed}x)"
    elif source == "seed":
        suffix = " (seed, unverified)"

    return f"- [{conf}] {text}{suffix}"


def _build_playbook_summary() -> str:
    """Load the playbook and return a formatted summary string."""
    data = _load_json(_PLAYBOOK_PATH)
    if data is None:
        return (
            "No playbook yet. Generate campaigns, log metrics, "
            "and analyze results to build one."
        )

    version = data.get("version", "?")
    learnings = data.get("learnings", [])

    if not learnings:
        return (
            "No playbook yet. Generate campaigns, log metrics, "
            "and analyze results to build one."
        )

    # Filter to active learnings (confidence >= threshold)
    active = [
        l for l in learnings
        if isinstance(l.get("confidence"), (int, float))
        and l["confidence"] >= _MIN_CONFIDENCE
    ]

    total_active = len(active)

    # Sort by confidence descending
    active.sort(key=lambda l: l.get("confidence", 0), reverse=True)

    # Truncate to top N
    active = active[:_MAX_LEARNINGS]

    # Group by category
    by_category: dict[str, list[dict]] = defaultdict(list)
    for l in active:
        category = l.get("category", "uncategorized")
        by_category[category].append(l)

    # Build formatted output
    lines: list[str] = [f"## Current Playbook (v{version}, {total_active} learnings)"]

    for category in sorted(by_category.keys()):
        items = by_category[category]
        lines.append("")
        lines.append(f"### {category.title()} (confidence: high to low)")
        for item in items:
            lines.append(_format_learning(item))

    return "\n".join(lines)


def _build_recent_performance() -> str:
    """Scan campaigns and return a formatted snapshot of the most recent ones."""
    if not _CAMPAIGNS_DIR.exists() or not _CAMPAIGNS_DIR.is_dir():
        return "No campaigns yet."

    campaigns: list[dict] = []

    for campaign_dir in _CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue

        brief_path = campaign_dir / "brief.json"
        brief = _load_json(brief_path)
        if brief is None:
            continue

        # Count variants
        variants_path = campaign_dir / "variants.json"
        num_variants = 0
        variants_data = _load_json(variants_path)
        if isinstance(variants_data, list):
            num_variants = len(variants_data)

        # Check if metrics exist
        metrics_path = campaign_dir / "metrics.json"
        has_metrics = metrics_path.exists()

        campaigns.append({
            "campaign_id": brief.get("campaign_id", campaign_dir.name),
            "channel": brief.get("channel", "unknown"),
            "status": brief.get("status", "unknown"),
            "num_variants": num_variants,
            "has_metrics": has_metrics,
            "created_at": brief.get("created_at", ""),
        })

    if not campaigns:
        return "No campaigns yet."

    # Sort by created_at descending, take most recent N
    campaigns.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    campaigns = campaigns[:_MAX_RECENT_CAMPAIGNS]

    lines: list[str] = ["## Recent Campaigns"]
    lines.append("")

    for i, c in enumerate(campaigns, 1):
        metrics_label = "yes" if c["has_metrics"] else "no"
        variants_label = (
            f"{c['num_variants']} variant{'s' if c['num_variants'] != 1 else ''}"
        )
        lines.append(
            f"{i}. {c['campaign_id']} "
            f"({c['channel']}, {c['status']}) "
            f"-- {variants_label}, metrics: {metrics_label}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 4 helpers
# ---------------------------------------------------------------------------

def _build_active_ab_tests_summary() -> str:
    """Scan campaigns for active A/B tests (COLLECTING/WAITING state)."""
    if not _CAMPAIGNS_DIR.exists():
        return ""

    active_tests: list[dict] = []
    for campaign_dir in _CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue
        state_path = campaign_dir / "ab_test_state.json"
        if not state_path.exists():
            continue
        state = _load_json(state_path)
        if state is None:
            continue
        if state.get("state") in ("COLLECTING", "WAITING", "ANALYZING"):
            active_tests.append({
                "test_id": state.get("test_id", ""),
                "campaign_id": state.get("campaign_id", campaign_dir.name),
                "state": state.get("state"),
                "hypothesis": state.get("hypothesis", ""),
                "next_check_at": state.get("next_check_at", ""),
            })

    if not active_tests:
        return ""

    lines = ["## Active A/B Tests", ""]
    for t in active_tests:
        lines.append(
            f"- {t['test_id']} ({t['campaign_id']}): {t['state']} "
            f"— \"{t['hypothesis']}\" — next check: {t['next_check_at']}"
        )
    return "\n".join(lines)


def _build_pending_transfers_summary() -> str:
    """Scan orchestration/transfers/ for pending cross-channel transfers."""
    transfers_dir = _ORCHESTRATION_DIR / "transfers"
    if not transfers_dir.exists():
        return ""

    pending: list[dict] = []
    for tf in transfers_dir.iterdir():
        if not tf.suffix == ".json":
            continue
        data = _load_json(tf)
        if data is None:
            continue
        if data.get("status") in ("proposed", "testing"):
            pending.append({
                "transfer_id": data.get("transfer_id", tf.stem),
                "source_channel": data.get("source_channel", ""),
                "target_channel": data.get("target_channel", ""),
                "hypothesis": data.get("hypothesis", ""),
                "status": data.get("status", ""),
            })

    if not pending:
        return ""

    lines = ["## Pending Cross-Channel Transfers", ""]
    for t in pending:
        lines.append(
            f"- {t['transfer_id']}: {t['source_channel']}→{t['target_channel']} "
            f"({t['status']}) — \"{t['hypothesis']}\""
        )
    return "\n".join(lines)


def _build_recent_anomalies() -> str:
    """Scan reports for recent anomaly alerts."""
    if not _REPORTS_DIR.exists():
        return ""

    anomalies: list[dict] = []
    for report_file in _REPORTS_DIR.iterdir():
        if not report_file.suffix == ".json":
            continue
        data = _load_json(report_file)
        if data is None:
            continue
        if data.get("report_type") != "anomaly_alerts":
            continue
        for alert in data.get("anomalies", [])[:5]:
            anomalies.append(alert)

    if not anomalies:
        return ""

    lines = ["## Recent Anomalies", ""]
    for a in anomalies[:5]:
        lines.append(
            f"- {a.get('channel', '?')}/{a.get('metric', '?')}: "
            f"{a.get('direction', '?')} (z={a.get('z_score', '?')})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Context factory -- the entry point referenced in agent.yml
# ---------------------------------------------------------------------------

@context_factory
def build_copy_context(variables):
    """Build context with skills discovery, playbook summary, and recent
    campaign performance for injection into the system prompt."""

    # 1. Discover skills
    try:
        skill_roots = [_SKILLS_DIR]
        available_skills_block = build_available_skills_block(skill_roots)
    except Exception:
        available_skills_block = "<!-- No skills discovered -->"

    # 2. Load playbook summary
    try:
        playbook_summary = _build_playbook_summary()
    except Exception:
        playbook_summary = (
            "No playbook yet. Generate campaigns, log metrics, "
            "and analyze results to build one."
        )

    # 3. Load recent performance snapshot
    try:
        recent_performance = _build_recent_performance()
    except Exception:
        recent_performance = "No campaigns yet."

    # 4. Load active A/B tests summary (Phase 4)
    try:
        active_ab_tests_summary = _build_active_ab_tests_summary()
    except Exception:
        active_ab_tests_summary = ""

    # 5. Load pending cross-channel transfers (Phase 4)
    try:
        pending_transfers_summary = _build_pending_transfers_summary()
    except Exception:
        pending_transfers_summary = ""

    # 6. Load recent anomalies (Phase 4)
    try:
        recent_anomalies = _build_recent_anomalies()
    except Exception:
        recent_anomalies = ""

    # 7. Return template variables
    return {
        "available_skills_block": available_skills_block,
        "playbook_summary": playbook_summary,
        "recent_performance": recent_performance,
        "active_ab_tests_summary": active_ab_tests_summary,
        "pending_transfers_summary": pending_transfers_summary,
        "recent_anomalies": recent_anomalies,
    }
