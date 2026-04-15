"""
Knowledge management tools for the Copy Agent.

Provides tools to save audience insights, competitor analysis notes,
and search across all accumulated knowledge for informed copy decisions.

All data is persisted as JSON files under data/knowledge/.
Thread safety on writes is provided by filelock.
"""

import json
from datetime import datetime
from pathlib import Path

from filelock import FileLock
from omniagents import function_tool

# ---------------------------------------------------------------------------
# Paths -- DATA_DIR is always <agent-root>/data
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
KNOWLEDGE_DIR: Path = DATA_DIR / "knowledge"

VALID_CATEGORIES = {
    "demographics",
    "pain_points",
    "motivations",
    "language",
    "objections",
    "preferences",
}

VALID_SOURCES = {
    "user_input",
    "campaign_analysis",
    "web_research",
    "competitor_study",
}

VALID_CHANNELS = {"email", "sms", "seo", "ad", "general"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict | list:
    """Read and return parsed JSON from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict | list) -> None:
    """Write JSON atomically using a .lock file next to the target."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file, returning None if it does not exist."""
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def _audiences_path() -> Path:
    return KNOWLEDGE_DIR / "audiences.json"


def _competitors_path() -> Path:
    return KNOWLEDGE_DIR / "competitors.json"


def _index_path() -> Path:
    return KNOWLEDGE_DIR / "index.json"


def _next_id(prefix: str, existing_items: list[dict]) -> str:
    """Generate the next auto-incrementing ID with the given prefix.

    Scans existing items for IDs matching the pattern {prefix}_NNN and
    returns the next one in sequence.
    """
    max_num = 0
    for item in existing_items:
        item_id = item.get("id", "")
        if item_id.startswith(f"{prefix}_"):
            try:
                num = int(item_id.split("_")[1])
                if num > max_num:
                    max_num = num
            except (IndexError, ValueError):
                pass
    return f"{prefix}_{max_num + 1:03d}"


def _update_index(entry_id: str, entry_type: str, searchable_text: str) -> None:
    """Add or update an entry in the search index.

    The index stores a flat list of records with id, type, and lowercased
    searchable text for fast keyword lookups.
    """
    index_path = _index_path()
    lock_path = index_path.with_suffix(index_path.suffix + ".lock")

    with FileLock(str(lock_path)):
        index_data = _load_json(index_path)
        if index_data is None:
            index_data = []

        # Remove existing entry with same id if present (update case)
        index_data = [e for e in index_data if e.get("id") != entry_id]

        index_data.append({
            "id": entry_id,
            "type": entry_type,
            "text": searchable_text.lower(),
        })

        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 1: save_audience_insight
# ---------------------------------------------------------------------------

@function_tool
def save_audience_insight(
    audience_name: str,
    insight: str,
    category: str,
    source: str,
    tags: str = "",
) -> str:
    """Save an audience research insight for future copy reference.

    Stores audience-level observations such as pain points, motivations,
    language patterns, and demographic details. Deduplicates by checking
    for similar insights within the same audience (substring match).

    Args:
        audience_name: The audience segment name (e.g. 'SaaS founders',
            'E-commerce marketers').
        insight: The actual insight text describing what was learned.
        category: The insight category. Must be one of: demographics,
            pain_points, motivations, language, objections, preferences.
        source: Where this insight came from. Must be one of: user_input,
            campaign_analysis, web_research, competitor_study.
        tags: Comma-separated tags for search (e.g. 'pricing,objection,saas').
    """
    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    category = category.lower().strip()
    if category not in VALID_CATEGORIES:
        return (
            f"Error: Invalid category '{category}'. "
            f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}."
        )

    source = source.lower().strip()
    if source not in VALID_SOURCES:
        return (
            f"Error: Invalid source '{source}'. "
            f"Must be one of: {', '.join(sorted(VALID_SOURCES))}."
        )

    audience_name = audience_name.strip()
    insight = insight.strip()

    if not audience_name:
        return "Error: audience_name cannot be empty."
    if not insight:
        return "Error: insight cannot be empty."

    # Parse tags
    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []

    # ------------------------------------------------------------------
    # Load or create audiences file
    # ------------------------------------------------------------------
    audiences_path = _audiences_path()
    lock_path = audiences_path.with_suffix(audiences_path.suffix + ".lock")

    with FileLock(str(lock_path)):
        data = _load_json(audiences_path)
        if data is None:
            data = []

        # --------------------------------------------------------------
        # Deduplication: check for similar insight in the same audience
        # --------------------------------------------------------------
        insight_lower = insight.lower()
        for existing in data:
            if existing.get("audience_name", "").lower() == audience_name.lower():
                existing_insight = existing.get("insight", "").lower()
                if (
                    insight_lower in existing_insight
                    or existing_insight in insight_lower
                ):
                    return (
                        f"Duplicate detected: A similar insight already exists for "
                        f"'{audience_name}'.\n"
                        f"  Existing [{existing.get('id')}]: \"{existing.get('insight')}\"\n"
                        f"No new record created."
                    )

        # --------------------------------------------------------------
        # Generate ID and create entry
        # --------------------------------------------------------------
        new_id = _next_id("aud", data)
        entry = {
            "id": new_id,
            "audience_name": audience_name,
            "insight": insight,
            "category": category,
            "source": source,
            "tags": tag_list,
            "created_at": datetime.now().isoformat(),
        }
        data.append(entry)

        # Persist
        audiences_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audiences_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Update search index
    searchable = " ".join([
        audience_name, insight, category, source, " ".join(tag_list),
    ])
    _update_index(new_id, "audience", searchable)

    return (
        f"Audience insight saved successfully.\n"
        f"  ID: {new_id}\n"
        f"  Audience: {audience_name}\n"
        f"  Category: {category}\n"
        f"  Source: {source}\n"
        f"  Tags: {', '.join(tag_list) if tag_list else '(none)'}\n"
        f"  Insight: {insight}"
    )


# ---------------------------------------------------------------------------
# Tool 2: save_competitor_note
# ---------------------------------------------------------------------------

@function_tool
def save_competitor_note(
    competitor_name: str,
    channel: str,
    observation: str,
    url: str = "",
    tags: str = "",
) -> str:
    """Save a competitive analysis observation for future reference.

    Stores observations about competitor copy, messaging, and marketing
    tactics across different channels.

    Args:
        competitor_name: The company or brand name being observed.
        channel: The marketing channel this observation relates to.
            Must be one of: email, sms, seo, ad, general.
        observation: What was observed about their copy or marketing approach.
        url: Optional URL where this was observed (e.g. from web_fetch).
        tags: Comma-separated tags for search (e.g. 'urgency,discount,subject-line').
    """
    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    channel = channel.lower().strip()
    if channel not in VALID_CHANNELS:
        return (
            f"Error: Invalid channel '{channel}'. "
            f"Must be one of: {', '.join(sorted(VALID_CHANNELS))}."
        )

    competitor_name = competitor_name.strip()
    observation = observation.strip()
    url = url.strip()

    if not competitor_name:
        return "Error: competitor_name cannot be empty."
    if not observation:
        return "Error: observation cannot be empty."

    # Parse tags
    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []

    # ------------------------------------------------------------------
    # Load or create competitors file
    # ------------------------------------------------------------------
    competitors_path = _competitors_path()
    lock_path = competitors_path.with_suffix(competitors_path.suffix + ".lock")

    with FileLock(str(lock_path)):
        data = _load_json(competitors_path)
        if data is None:
            data = []

        # --------------------------------------------------------------
        # Generate ID and create entry
        # --------------------------------------------------------------
        new_id = _next_id("comp", data)
        entry = {
            "id": new_id,
            "competitor_name": competitor_name,
            "channel": channel,
            "observation": observation,
            "url": url,
            "tags": tag_list,
            "created_at": datetime.now().isoformat(),
        }
        data.append(entry)

        # Persist
        competitors_path.parent.mkdir(parents=True, exist_ok=True)
        with open(competitors_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Update search index
    searchable = " ".join([
        competitor_name, channel, observation, url, " ".join(tag_list),
    ])
    _update_index(new_id, "competitor", searchable)

    return (
        f"Competitor note saved successfully.\n"
        f"  ID: {new_id}\n"
        f"  Competitor: {competitor_name}\n"
        f"  Channel: {channel}\n"
        f"  URL: {url or '(none)'}\n"
        f"  Tags: {', '.join(tag_list) if tag_list else '(none)'}\n"
        f"  Observation: {observation}"
    )


# ---------------------------------------------------------------------------
# Tool 3: search_knowledge
# ---------------------------------------------------------------------------

@function_tool
def search_knowledge(
    query: str,
    knowledge_type: str = "all",
    limit: int = 10,
) -> str:
    """Search across all stored knowledge — audience insights and competitor notes.

    Uses simple keyword matching: the query is split into words and each
    record is scored by the number of matching keywords found in its text
    content, tags, names, and categories. Results are sorted by relevance.

    Args:
        query: The search text (keywords to match against stored knowledge).
        knowledge_type: What to search. One of: 'audiences', 'competitors',
            'all'. Defaults to 'all'.
        limit: Maximum number of results to return. Defaults to 10.
    """
    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    valid_types = {"audiences", "competitors", "all"}
    knowledge_type = knowledge_type.lower().strip()
    if knowledge_type not in valid_types:
        return (
            f"Error: Invalid knowledge_type '{knowledge_type}'. "
            f"Must be one of: {', '.join(sorted(valid_types))}."
        )

    query = query.strip()
    if not query:
        return "Error: query cannot be empty."

    if limit < 1:
        limit = 10

    # Split query into lowercase keywords
    keywords = [w.lower() for w in query.split() if w.strip()]
    if not keywords:
        return "Error: query must contain at least one keyword."

    results: list[dict] = []

    # ------------------------------------------------------------------
    # Search audience insights
    # ------------------------------------------------------------------
    if knowledge_type in ("audiences", "all"):
        audience_data = _load_json(_audiences_path())
        if audience_data and isinstance(audience_data, list):
            for entry in audience_data:
                searchable = " ".join([
                    entry.get("audience_name", ""),
                    entry.get("insight", ""),
                    entry.get("category", ""),
                    entry.get("source", ""),
                    " ".join(entry.get("tags", [])),
                ]).lower()

                score = sum(1 for kw in keywords if kw in searchable)
                if score > 0:
                    results.append({
                        "type": "audience",
                        "id": entry.get("id", "?"),
                        "score": score,
                        "entry": entry,
                    })

    # ------------------------------------------------------------------
    # Search competitor notes
    # ------------------------------------------------------------------
    if knowledge_type in ("competitors", "all"):
        competitor_data = _load_json(_competitors_path())
        if competitor_data and isinstance(competitor_data, list):
            for entry in competitor_data:
                searchable = " ".join([
                    entry.get("competitor_name", ""),
                    entry.get("channel", ""),
                    entry.get("observation", ""),
                    entry.get("url", ""),
                    " ".join(entry.get("tags", [])),
                ]).lower()

                score = sum(1 for kw in keywords if kw in searchable)
                if score > 0:
                    results.append({
                        "type": "competitor",
                        "id": entry.get("id", "?"),
                        "score": score,
                        "entry": entry,
                    })

    # ------------------------------------------------------------------
    # Sort by relevance score (descending), then by ID for stable order
    # ------------------------------------------------------------------
    results.sort(key=lambda r: (-r["score"], r["id"]))
    results = results[:limit]

    if not results:
        scope = knowledge_type if knowledge_type != "all" else "audiences and competitors"
        return f"No results found for '{query}' in {scope}."

    # ------------------------------------------------------------------
    # Format output
    # ------------------------------------------------------------------
    lines = [
        f"Found {len(results)} result(s) for '{query}':",
        "",
    ]

    for i, result in enumerate(results, 1):
        entry = result["entry"]
        rtype = result["type"]
        score = result["score"]

        if rtype == "audience":
            lines.append(
                f"{i}. [{entry.get('id')}] (audience, score: {score})\n"
                f"   Audience: {entry.get('audience_name', '')}\n"
                f"   Category: {entry.get('category', '')}\n"
                f"   Insight: {entry.get('insight', '')}\n"
                f"   Source: {entry.get('source', '')} | "
                f"Tags: {', '.join(entry.get('tags', [])) or '(none)'}\n"
                f"   Created: {entry.get('created_at', '')}"
            )
        elif rtype == "competitor":
            lines.append(
                f"{i}. [{entry.get('id')}] (competitor, score: {score})\n"
                f"   Competitor: {entry.get('competitor_name', '')}\n"
                f"   Channel: {entry.get('channel', '')}\n"
                f"   Observation: {entry.get('observation', '')}\n"
                f"   URL: {entry.get('url', '') or '(none)'} | "
                f"Tags: {', '.join(entry.get('tags', [])) or '(none)'}\n"
                f"   Created: {entry.get('created_at', '')}"
            )
        lines.append("")

    return "\n".join(lines)
