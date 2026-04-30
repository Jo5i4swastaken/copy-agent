"""
Analysis tools for the Copy Agent.

Provides campaign analysis, playbook management, and learning persistence
for iterative copy optimization across email, SMS, SEO, and ad channels.
"""

from omniagents import function_tool
from pathlib import Path
from tools.lock import FileLock
from datetime import datetime, date
import json
import math

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Stop-words excluded from tag extraction
# ---------------------------------------------------------------------------
STOP_WORDS = {
    "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can",
    "for", "and", "nor", "but", "yet", "not",
    "with", "from", "into", "onto", "upon", "about",
    "that", "this", "these", "those", "then", "than",
    "what", "which", "when", "where", "who", "whom", "how",
    "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "only", "also", "very", "just",
    "over", "under", "after", "before", "between", "through",
    "during", "above", "below",
    "their", "they", "them", "your", "you", "our",
    "its", "his", "her", "she", "him",
    "all", "any", "same", "much", "many",
    "well", "back", "even", "still", "here", "there",
    "like", "make", "made", "take", "took", "give", "gave",
    "good", "best", "better", "worse", "worst",
    "work", "works", "worked", "working",
    "use", "used", "using",
    "show", "shows", "showed",
    "lead", "leads",
    "high", "higher", "low", "lower",
    "tend", "tends",
    "seem", "seems",
    "keep", "kept",
}

# Metrics where a higher value means better performance
POSITIVE_METRICS = {
    "open_rate",
    "click_rate",
    "conversion_rate",
    "roas",
    "revenue",
    "engagement_rate",
    "reply_rate",
    "forward_rate",
    "click_through_rate",
}

# Metrics where a lower value means better performance
NEGATIVE_METRICS = {
    "cost_per_click",
    "bounce_rate",
    "unsubscribe_rate",
    "opt_out_rate",
    "cost_per_acquisition",
    "spam_rate",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file, returning None if it does not exist."""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict | list) -> None:
    """Write data to a JSON file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _extract_tags(text: str) -> list[str]:
    """Extract simple keyword tags from a learning string."""
    words = text.lower().split()
    # Strip basic punctuation from each word
    cleaned = []
    for w in words:
        w = w.strip(".,;:!?\"'()[]{}")
        if len(w) > 3 and w not in STOP_WORDS and w.isalpha():
            cleaned.append(w)
    # Deduplicate while preserving order
    seen = set()
    tags = []
    for w in cleaned:
        if w not in seen:
            seen.add(w)
            tags.append(w)
    return tags


def _metric_is_positive(metric_name: str) -> bool:
    """Determine if a metric is 'positive' (higher is better).

    Falls back to True for unknown metrics so the tool still works
    with custom metric names.
    """
    name = metric_name.lower()
    if name in NEGATIVE_METRICS:
        return False
    return True


def _format_value(value: float) -> str:
    """Format a numeric value for display."""
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    return f"{value:.4f}" if abs(value) < 0.01 else f"{value:.2f}"


def _pct_diff(best: float, worst: float) -> str:
    """Calculate percentage difference between best and worst."""
    if worst == 0:
        return "N/A (worst is 0)"
    diff = abs(best - worst) / abs(worst) * 100
    return f"{diff:.1f}%"


# ---------------------------------------------------------------------------
# Tool 1: analyze_campaign
# ---------------------------------------------------------------------------

@function_tool
def analyze_campaign(campaign_id: str) -> str:
    """Analyze a campaign by comparing variant performance across all logged metrics.

    Returns a structured report with metrics comparison, winners per metric,
    key differences between winning and losing variants, and suggested learnings.
    Requires metrics for at least 2 variants to produce a meaningful comparison.

    Args:
        campaign_id: The unique identifier for the campaign to analyze.
    """
    campaign_dir = DATA_DIR / "campaigns" / campaign_id
    variants_path = campaign_dir / "variants.json"
    metrics_path = campaign_dir / "metrics.json"
    brief_path = campaign_dir / "brief.json"

    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    variants_data = _load_json(variants_path)
    metrics_data = _load_json(metrics_path)
    brief_data = _load_json(brief_path)

    if variants_data is None:
        return f"Campaign '{campaign_id}' not found or has no variants file at {variants_path}."
    if metrics_data is None:
        return f"Campaign '{campaign_id}' has no metrics file at {metrics_path}. Log metrics first."

    # Normalize: variants can be a list or a dict with a "variants" key
    variants_list = variants_data if isinstance(variants_data, list) else variants_data.get("variants", [])
    metrics_list = metrics_data if isinstance(metrics_data, list) else metrics_data.get("metrics", [])

    if not metrics_list:
        return "No metrics logged yet for this campaign. Use log_metrics to add performance data first."

    # ------------------------------------------------------------------
    # Group metrics by variant_id
    # ------------------------------------------------------------------
    variant_metrics: dict[str, dict[str, list[float]]] = {}
    for entry in metrics_list:
        vid = entry.get("variant_id", "unknown")
        mtype = entry.get("metric_type") or entry.get("type") or entry.get("name")
        value = entry.get("value")
        if mtype is None or value is None:
            continue
        mtype = mtype.lower().strip()
        variant_metrics.setdefault(vid, {}).setdefault(mtype, []).append(float(value))

    # Check minimum variant count
    variants_with_metrics = list(variant_metrics.keys())
    if len(variants_with_metrics) < 2:
        return "Not enough data for comparison. Need metrics for at least 2 variants."

    # Build a lookup of variant details by id
    variant_lookup: dict[str, dict] = {}
    for v in variants_list:
        vid = v.get("id") or v.get("variant_id")
        if vid:
            variant_lookup[vid] = v

    # ------------------------------------------------------------------
    # Compute averages per variant per metric
    # ------------------------------------------------------------------
    all_metric_types: set[str] = set()
    variant_averages: dict[str, dict[str, float]] = {}
    for vid, mdict in variant_metrics.items():
        variant_averages[vid] = {}
        for mtype, values in mdict.items():
            all_metric_types.add(mtype)
            variant_averages[vid][mtype] = sum(values) / len(values)

    sorted_metrics = sorted(all_metric_types)

    # ------------------------------------------------------------------
    # Determine winner per metric
    # ------------------------------------------------------------------
    winners: dict[str, dict] = {}  # metric -> {winner_id, winner_val, loser_id, loser_val, pct_diff, direction}

    for mtype in sorted_metrics:
        scores: list[tuple[str, float]] = []
        for vid in variants_with_metrics:
            avg = variant_averages.get(vid, {}).get(mtype)
            if avg is not None:
                scores.append((vid, avg))

        if len(scores) < 2:
            continue

        positive = _metric_is_positive(mtype)
        if positive:
            scores.sort(key=lambda x: x[1], reverse=True)
        else:
            scores.sort(key=lambda x: x[1])  # lowest first for negative

        best_id, best_val = scores[0]
        worst_id, worst_val = scores[-1]

        winners[mtype] = {
            "winner_id": best_id,
            "winner_val": best_val,
            "loser_id": worst_id,
            "loser_val": worst_val,
            "pct_diff": _pct_diff(best_val, worst_val),
            "direction": "higher is better" if positive else "lower is better",
        }

    # ------------------------------------------------------------------
    # Identify key differences between winners and losers
    # ------------------------------------------------------------------
    compare_fields = [
        "subject_line", "tone", "cta", "call_to_action",
        "content_length", "body", "headline", "description",
        "preheader", "sender_name", "send_time", "template",
        "personalization", "emoji_usage", "urgency_level",
        "offer_type", "discount", "channel",
    ]

    differences: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()

    for mtype, info in winners.items():
        w_variant = variant_lookup.get(info["winner_id"], {})
        l_variant = variant_lookup.get(info["loser_id"], {})
        pair = (info["winner_id"], info["loser_id"])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        for field in compare_fields:
            w_val = w_variant.get(field)
            l_val = l_variant.get(field)
            if w_val is not None and l_val is not None and str(w_val) != str(l_val):
                # Truncate long values for readability
                w_display = str(w_val)[:80] + ("..." if len(str(w_val)) > 80 else "")
                l_display = str(l_val)[:80] + ("..." if len(str(l_val)) > 80 else "")
                differences.append(
                    f"  - {field}: Winner ({info['winner_id']}): \"{w_display}\" vs Loser ({info['loser_id']}): \"{l_display}\""
                )

    # ------------------------------------------------------------------
    # Build the report
    # ------------------------------------------------------------------
    lines: list[str] = []

    # Campaign summary
    lines.append("=" * 60)
    lines.append(f"CAMPAIGN ANALYSIS: {campaign_id}")
    lines.append("=" * 60)
    lines.append("")

    if brief_data:
        brief_name = brief_data.get("name") or brief_data.get("campaign_name") or campaign_id
        brief_channel = brief_data.get("channel", "unknown")
        brief_goal = brief_data.get("goal") or brief_data.get("objective", "not specified")
        lines.append(f"Campaign: {brief_name}")
        lines.append(f"Channel: {brief_channel}")
        lines.append(f"Goal: {brief_goal}")
        lines.append("")

    lines.append(f"Variants analyzed: {len(variants_with_metrics)}")
    lines.append(f"Metrics tracked: {', '.join(sorted_metrics)}")
    lines.append("")

    # Metrics comparison table
    lines.append("-" * 60)
    lines.append("METRICS COMPARISON")
    lines.append("-" * 60)
    lines.append("")

    for mtype in sorted_metrics:
        lines.append(f"  {mtype} ({'higher is better' if _metric_is_positive(mtype) else 'lower is better'}):")
        for vid in variants_with_metrics:
            avg = variant_averages.get(vid, {}).get(mtype)
            if avg is not None:
                marker = ""
                if mtype in winners:
                    if vid == winners[mtype]["winner_id"]:
                        marker = " << WINNER"
                    elif vid == winners[mtype]["loser_id"]:
                        marker = " << WORST"
                lines.append(f"    {vid}: {_format_value(avg)}{marker}")
            else:
                lines.append(f"    {vid}: (no data)")
        if mtype in winners:
            lines.append(f"    Gap: {winners[mtype]['pct_diff']} difference")
        lines.append("")

    # Winner summary
    lines.append("-" * 60)
    lines.append("WINNERS PER METRIC")
    lines.append("-" * 60)
    lines.append("")

    for mtype in sorted_metrics:
        if mtype in winners:
            w = winners[mtype]
            lines.append(
                f"  {mtype}: {w['winner_id']} ({_format_value(w['winner_val'])}) "
                f"beats {w['loser_id']} ({_format_value(w['loser_val'])}) by {w['pct_diff']}"
            )
    lines.append("")

    # Count overall wins per variant
    win_counts: dict[str, int] = {}
    for info in winners.values():
        win_counts[info["winner_id"]] = win_counts.get(info["winner_id"], 0) + 1

    if win_counts:
        overall_winner = max(win_counts, key=lambda k: win_counts[k])
        lines.append(f"Overall best performer: {overall_winner} (won {win_counts[overall_winner]}/{len(winners)} metrics)")
        lines.append("")

    # Key differences
    lines.append("-" * 60)
    lines.append("KEY DIFFERENCES BETWEEN WINNERS AND LOSERS")
    lines.append("-" * 60)
    lines.append("")

    if differences:
        for diff in differences:
            lines.append(diff)
    else:
        lines.append("  No structural differences detected in variant fields.")
        lines.append("  (Variants may differ in copy text — review the actual content.)")
    lines.append("")

    # Suggested learnings
    lines.append("-" * 60)
    lines.append("SUGGESTED LEARNINGS TO SAVE")
    lines.append("-" * 60)
    lines.append("")

    suggested_learnings: list[str] = []
    for mtype, info in winners.items():
        w_variant = variant_lookup.get(info["winner_id"], {})
        # Look for distinctive attributes of the winner
        for field in ["tone", "cta", "call_to_action", "subject_line", "urgency_level", "offer_type"]:
            w_val = w_variant.get(field)
            if w_val:
                channel = brief_data.get("channel", "general") if brief_data else "general"
                learning = (
                    f"For {mtype}: Variant with {field}=\"{str(w_val)[:60]}\" outperformed by {info['pct_diff']}. "
                    f"Consider using similar {field} in future {channel} campaigns."
                )
                suggested_learnings.append(learning)

    if suggested_learnings:
        for i, sl in enumerate(suggested_learnings, 1):
            lines.append(f"  {i}. {sl}")
        lines.append("")
        lines.append("Use save_learning to persist any of these insights to the playbook.")
    else:
        lines.append("  No specific attribute-level learnings could be extracted.")
        lines.append("  Review the variant copy manually and save learnings about what worked.")
    lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: read_playbook
# ---------------------------------------------------------------------------

@function_tool
def read_playbook() -> str:
    """Read the marketing playbook containing accumulated learnings from past campaigns.

    Returns all learnings organized by category (email, sms, seo, ad, general)
    with confidence levels, evidence, and confirmation counts. Use this to inform
    future copy decisions with data-driven insights.
    """
    playbook_path = DATA_DIR / "playbook.json"
    lock_path = playbook_path.with_suffix(".json.lock")

    with FileLock(lock_path):
        data = _load_json(playbook_path)

    if data is None or not data.get("learnings"):
        return "Playbook is empty. Start by creating campaigns and logging metrics."

    learnings = data["learnings"]
    version = data.get("version", 1)
    last_updated = data.get("last_updated", "unknown")

    # Group by category
    categories: dict[str, list[dict]] = {}
    for entry in learnings:
        cat = entry.get("category", "general")
        categories.setdefault(cat, []).append(entry)

    # Desired display order
    category_order = ["email", "sms", "seo", "ad", "general"]
    # Include any categories not in the predefined order
    all_cats = category_order + [c for c in sorted(categories.keys()) if c not in category_order]

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("MARKETING PLAYBOOK")
    lines.append(f"Version: {version} | Last updated: {last_updated}")
    lines.append(f"Total learnings: {len(learnings)}")
    lines.append("=" * 60)
    lines.append("")

    confidence_labels = {0.3: "LOW", 0.6: "MEDIUM", 0.9: "HIGH"}

    for cat in all_cats:
        entries = categories.get(cat)
        if not entries:
            continue

        lines.append("-" * 60)
        lines.append(f"  {cat.upper()} ({len(entries)} learnings)")
        lines.append("-" * 60)
        lines.append("")

        for entry in entries:
            eid = entry.get("id", "?")
            learning_text = entry.get("learning", "(no text)")
            confidence = entry.get("confidence", 0.3)
            confidence_label = confidence_labels.get(confidence, f"{confidence:.1f}")
            evidence = entry.get("evidence", "")
            confirmed = entry.get("times_confirmed", 0)
            contradicted = entry.get("times_contradicted", 0)
            first_obs = entry.get("first_observed", "unknown")
            last_conf = entry.get("last_confirmed", "unknown")
            tags = entry.get("tags", [])
            source = entry.get("source", "")
            deactivated = entry.get("deactivated", False)

            prefix = "  [DEACTIVATED] " if deactivated else "  "
            lines.append(f"{prefix}[{eid}] {learning_text}")
            lines.append(f"    Confidence: {confidence_label} ({confidence})")
            if evidence:
                lines.append(f"    Evidence: {evidence}")
            lines.append(f"    Confirmed: {confirmed}x | Contradicted: {contradicted}x")
            lines.append(f"    Observed: {first_obs} | Last confirmed: {last_conf}")
            if tags:
                lines.append(f"    Tags: {', '.join(tags)}")
            if source:
                lines.append(f"    Source: {source}")
            if deactivated:
                lines.append(f"    Status: DEACTIVATED (excluded from context injection)")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 3: save_learning
# ---------------------------------------------------------------------------

@function_tool
def save_learning(
    category: str,
    learning: str,
    evidence: str = "",
    confidence: str = "low",
) -> str:
    """Save a new learning to the marketing playbook for future reference.

    Learnings are data-driven insights extracted from campaign analysis that help
    improve future copy. Duplicate learnings are detected and rejected. If a new
    learning confirms an existing seed entry, the seed's confidence is boosted.

    Args:
        category: The marketing channel this learning applies to. One of: email, sms, seo, ad, general.
        learning: The insight or pattern observed, written as an actionable statement.
        evidence: Supporting data or campaign reference that validates this learning.
        confidence: Confidence level for this learning. One of: low, medium, high. Default is low for new data-driven learnings.
    """
    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    valid_categories = {"email", "sms", "seo", "ad", "general"}
    category = category.lower().strip()
    if category not in valid_categories:
        return f"Invalid category '{category}'. Must be one of: {', '.join(sorted(valid_categories))}"

    confidence_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
    confidence_lower = confidence.lower().strip()
    if confidence_lower not in confidence_map:
        return f"Invalid confidence '{confidence}'. Must be one of: low, medium, high"

    confidence_value = confidence_map[confidence_lower]
    today = date.today().isoformat()

    # ------------------------------------------------------------------
    # Load or create playbook with file lock
    # ------------------------------------------------------------------
    playbook_path = DATA_DIR / "playbook.json"
    lock_path = playbook_path.with_suffix(".json.lock")

    with FileLock(lock_path):
        data = _load_json(playbook_path)
        if data is None:
            data = {
                "learnings": [],
                "version": 1,
                "last_updated": today,
            }

        learnings_list: list[dict] = data.get("learnings", [])

        # --------------------------------------------------------------
        # Duplicate check: simple substring on lowercased text
        # --------------------------------------------------------------
        learning_lower = learning.lower().strip()
        for existing in learnings_list:
            existing_text = existing.get("learning", "").lower().strip()
            # Check if the new learning is a substring of an existing one
            # or if an existing one is a substring of the new learning
            if (
                learning_lower in existing_text
                or existing_text in learning_lower
            ):
                # Skip deactivated learnings — treat them as non-matching
                # so a fresh version of the learning can be saved
                if existing.get("deactivated"):
                    continue

                # If this confirms a seed entry or low-confidence entry, boost it
                if existing.get("source") == "seed" or existing.get("confidence", 0) == 0.3:
                    existing["times_confirmed"] = existing.get("times_confirmed", 0) + 1
                    existing["last_confirmed"] = today
                    # Boost confidence: move toward medium if currently low
                    if existing["confidence"] < 0.6 and existing["times_confirmed"] >= 2:
                        existing["confidence"] = 0.6
                    elif existing["confidence"] < 0.9 and existing["times_confirmed"] >= 5:
                        existing["confidence"] = 0.9

                    # ----------------------------------------------------------
                    # Auto-promotion: if confirmed >= 3 times and confidence is
                    # still below high, auto-promote to 0.9 (high)
                    # ----------------------------------------------------------
                    if (
                        existing["times_confirmed"] >= 3
                        and existing.get("confidence", 0) < 0.9
                    ):
                        existing["confidence"] = 0.9

                    # ----------------------------------------------------------
                    # Auto-deactivation: if contradicted >= 3 times and
                    # confirmed < 2, set confidence to 0 and deactivate.
                    # Deactivated learnings are kept for history but excluded
                    # from context injection.
                    # ----------------------------------------------------------
                    if (
                        existing.get("times_contradicted", 0) >= 3
                        and existing.get("times_confirmed", 0) < 2
                    ):
                        existing["confidence"] = 0.0
                        existing["deactivated"] = True

                    # ----------------------------------------------------------
                    # Confidence decay: placeholder for future implementation.
                    # When implemented, decay would reduce confidence gradually
                    # for learnings that have not been confirmed recently.
                    # Example approach: apply a time-based decay factor here
                    # based on (today - last_confirmed).days, e.g.:
                    #   days_since = (date.today() - parse(existing["last_confirmed"])).days
                    #   if days_since > 90 and existing["confidence"] > 0.3:
                    #       existing["confidence"] = max(0.3, existing["confidence"] - 0.1)
                    # ----------------------------------------------------------

                    data["last_updated"] = today
                    data["version"] = data.get("version", 1) + 1
                    _save_json(playbook_path, data)

                    status_note = ""
                    if existing.get("deactivated"):
                        status_note = " [DEACTIVATED — contradicted too often]"

                    return (
                        f"Similar learning already exists: [{existing.get('id')}] \"{existing.get('learning')}\"\n"
                        f"Confirmed it (+1). Times confirmed: {existing['times_confirmed']}. "
                        f"Confidence now: {existing['confidence']}{status_note}"
                    )
                return f"Similar learning already exists: [{existing.get('id')}] \"{existing.get('learning')}\""

        # --------------------------------------------------------------
        # Generate new ID
        # --------------------------------------------------------------
        existing_ids = [e.get("id", "") for e in learnings_list]
        max_num = 0
        for eid in existing_ids:
            if eid.startswith("learn_"):
                try:
                    num = int(eid.split("_")[1])
                    if num > max_num:
                        max_num = num
                except (IndexError, ValueError):
                    pass
        new_id = f"learn_{max_num + 1:03d}"

        # --------------------------------------------------------------
        # Extract tags
        # --------------------------------------------------------------
        tags = _extract_tags(learning)

        # --------------------------------------------------------------
        # Create and append the new entry
        # --------------------------------------------------------------
        new_entry = {
            "id": new_id,
            "category": category,
            "learning": learning,
            "evidence": evidence,
            "confidence": confidence_value,
            "times_confirmed": 0,
            "times_contradicted": 0,
            "first_observed": today,
            "last_confirmed": today,
            "tags": tags,
        }

        learnings_list.append(new_entry)
        data["learnings"] = learnings_list
        data["version"] = data.get("version", 1) + 1
        data["last_updated"] = today

        _save_json(playbook_path, data)

    return (
        f"Learning saved successfully.\n"
        f"  ID: {new_id}\n"
        f"  Category: {category}\n"
        f"  Learning: {learning}\n"
        f"  Confidence: {confidence_lower} ({confidence_value})\n"
        f"  Evidence: {evidence or '(none provided)'}\n"
        f"  Tags: {', '.join(tags) if tags else '(none)'}"
    )


# ---------------------------------------------------------------------------
# Tool 4: design_ab_test
# ---------------------------------------------------------------------------

@function_tool
def design_ab_test(
    campaign_id: str,
    hypothesis: str,
    variable: str,
    variants_description: str,
) -> str:
    """Design a structured A/B test plan for a campaign.

    Creates a test plan that specifies a control and treatment, the metrics to
    track, a minimum sample size recommendation, and expected duration. Saves
    the plan to the campaign directory for reference during variant generation.

    Args:
        campaign_id: The campaign to attach this A/B test plan to.
        hypothesis: The hypothesis being tested, e.g. "Subject lines with numbers will have higher open rates".
        variable: The copy variable being tested, e.g. tone, CTA style, subject approach, length, emoji usage.
        variants_description: A description of the variants, e.g. "Control: professional tone. Treatment: casual/conversational tone."
    """
    campaign_dir = DATA_DIR / "campaigns" / campaign_id
    brief_path = campaign_dir / "brief.json"

    if not brief_path.exists():
        return f"Campaign '{campaign_id}' not found. Create the campaign first with generate_copy."

    brief_data = _load_json(brief_path)
    channel = brief_data.get("channel", "unknown") if brief_data else "unknown"

    # ------------------------------------------------------------------
    # Parse control/treatment from variants_description
    # ------------------------------------------------------------------
    # Try to split on common delimiters
    parts = variants_description.split(".")
    control_desc = parts[0].strip() if len(parts) >= 1 else "Control variant"
    treatment_desc = parts[1].strip() if len(parts) >= 2 else "Treatment variant"

    # Clean up labels if they contain "Control:" or "Treatment:" prefixes
    for prefix in ["control:", "control -", "control--"]:
        if control_desc.lower().startswith(prefix):
            control_desc = control_desc[len(prefix):].strip()
    for prefix in ["treatment:", "treatment -", "treatment--"]:
        if treatment_desc.lower().startswith(prefix):
            treatment_desc = treatment_desc[len(prefix):].strip()

    # ------------------------------------------------------------------
    # Determine metrics to track based on channel
    # ------------------------------------------------------------------
    channel_metrics = {
        "email": ["open_rate", "click_rate", "conversion_rate", "unsubscribe_rate"],
        "sms": ["click_rate", "conversion_rate", "opt_out_rate", "reply_rate"],
        "seo": ["click_rate", "search_position", "bounce_rate", "time_on_page"],
        "ad": ["click_rate", "conversion_rate", "cost_per_click", "roas"],
    }
    metrics_to_track = channel_metrics.get(channel, ["click_rate", "conversion_rate"])

    # Primary metric: pick the first one as the primary KPI
    primary_metric = metrics_to_track[0]

    # ------------------------------------------------------------------
    # Sample size recommendation
    # Simplified calculation: for detecting a 20% relative lift with
    # 80% power and 95% confidence, a common heuristic is ~400 per variant
    # for conversion-type metrics. Adjust based on expected baseline.
    # ------------------------------------------------------------------
    baseline_rates = {
        "open_rate": 0.20,
        "click_rate": 0.03,
        "conversion_rate": 0.02,
        "reply_rate": 0.01,
        "search_position": None,  # not rate-based
        "cost_per_click": None,   # not rate-based
        "roas": None,             # not rate-based
    }

    baseline = baseline_rates.get(primary_metric)
    if baseline and baseline > 0:
        # Approximate sample size per variant using:
        # n = 16 * p * (1-p) / (delta^2) where delta = 0.2 * p (20% relative MDE)
        mde = 0.20 * baseline
        if mde > 0:
            n_per_variant = math.ceil(16 * baseline * (1 - baseline) / (mde ** 2))
        else:
            n_per_variant = 500
    else:
        n_per_variant = 500  # default for non-rate metrics

    total_sample = n_per_variant * 2

    # Estimated duration based on channel typical send volumes
    channel_durations = {
        "email": "3-7 days (depending on list size and send frequency)",
        "sms": "2-5 days (depending on subscriber base)",
        "seo": "14-30 days (search ranking changes are slow)",
        "ad": "7-14 days (depending on daily budget and impressions)",
    }
    expected_duration = channel_durations.get(channel, "7-14 days")

    # ------------------------------------------------------------------
    # Build the test plan
    # ------------------------------------------------------------------
    test_plan = {
        "campaign_id": campaign_id,
        "channel": channel,
        "hypothesis": hypothesis,
        "variable_tested": variable,
        "control": {
            "description": control_desc,
            "variant_id": "control",
        },
        "treatment": {
            "description": treatment_desc,
            "variant_id": "treatment",
        },
        "primary_metric": primary_metric,
        "metrics_to_track": metrics_to_track,
        "sample_size": {
            "per_variant": n_per_variant,
            "total": total_sample,
            "note": "Based on detecting a 20% relative lift with ~80% power at 95% confidence.",
        },
        "expected_duration": expected_duration,
        "status": "designed",
        "created_at": datetime.now().isoformat(),
    }

    # ------------------------------------------------------------------
    # Save the test plan
    # ------------------------------------------------------------------
    ab_test_path = campaign_dir / "ab_test.json"
    lock_path = ab_test_path.with_suffix(".json.lock")
    with FileLock(lock_path):
        _save_json(ab_test_path, test_plan)

    # ------------------------------------------------------------------
    # Format the return report
    # ------------------------------------------------------------------
    lines = [
        "=" * 60,
        f"A/B TEST PLAN: {campaign_id}",
        "=" * 60,
        "",
        f"Hypothesis: {hypothesis}",
        f"Variable: {variable}",
        f"Channel: {channel}",
        "",
        "-" * 60,
        "VARIANTS",
        "-" * 60,
        f"  Control:   {control_desc}",
        f"  Treatment: {treatment_desc}",
        "",
        "-" * 60,
        "METRICS",
        "-" * 60,
        f"  Primary KPI: {primary_metric}",
        f"  Also tracking: {', '.join(metrics_to_track[1:])}",
        "",
        "-" * 60,
        "SAMPLE SIZE",
        "-" * 60,
        f"  Per variant: {n_per_variant:,}",
        f"  Total needed: {total_sample:,}",
        f"  Note: Based on detecting a 20% relative lift at 95% confidence.",
        "",
        "-" * 60,
        "DURATION",
        "-" * 60,
        f"  Expected: {expected_duration}",
        "",
        "=" * 60,
        f"Test plan saved to: data/campaigns/{campaign_id}/ab_test.json",
        "",
        "Next steps:",
        f"  1. Generate control variant with {variable} = \"{control_desc}\"",
        f"  2. Generate treatment variant with {variable} = \"{treatment_desc}\"",
        f"  3. Deploy both variants and collect metrics",
        f"  4. Log metrics with log_metrics and analyze with analyze_campaign",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 5: identify_patterns
# ---------------------------------------------------------------------------

@function_tool
def identify_patterns(
    channel: str = "all",
    min_campaigns: int = 2,
) -> str:
    """Cross-campaign pattern recognition across all completed campaigns.

    Scans campaigns for the specified channel, groups variants by attributes
    (tone, CTA style, subject approach), and compares average metric performance
    across groups. Identifies statistically meaningful patterns like "casual tone
    averages 24% open rate vs 18% for professional".

    Args:
        channel: Channel to analyze — one of: email, sms, seo, ad, all. Default is all.
        min_campaigns: Minimum number of campaigns required to identify patterns. Default is 2.
    """
    campaigns_dir = DATA_DIR / "campaigns"
    if not campaigns_dir.exists():
        return "No campaigns directory found. Create campaigns first."

    # ------------------------------------------------------------------
    # Scan all campaigns and collect variant+metric data
    # ------------------------------------------------------------------
    all_variant_data: list[dict] = []  # Each entry: variant fields + averaged metrics
    campaign_count = 0
    channel_lower = channel.lower().strip()

    for campaign_path in campaigns_dir.iterdir():
        if not campaign_path.is_dir():
            continue

        brief_path = campaign_path / "brief.json"
        variants_path = campaign_path / "variants.json"
        metrics_path = campaign_path / "metrics.json"

        if not brief_path.exists() or not metrics_path.exists():
            continue

        brief_data = _load_json(brief_path)
        if brief_data is None:
            continue

        camp_channel = brief_data.get("channel", "unknown").lower()
        if channel_lower != "all" and camp_channel != channel_lower:
            continue

        variants_data = _load_json(variants_path)
        metrics_data = _load_json(metrics_path)

        if not variants_data or not metrics_data:
            continue

        variants_list = variants_data if isinstance(variants_data, list) else variants_data.get("variants", [])
        metrics_list = metrics_data if isinstance(metrics_data, list) else metrics_data.get("metrics", [])

        if not metrics_list:
            continue

        campaign_count += 1
        campaign_id = brief_data.get("campaign_id", campaign_path.name)

        # Build variant lookup
        variant_lookup: dict[str, dict] = {}
        for v in variants_list:
            vid = v.get("variant_id") or v.get("id")
            if vid:
                variant_lookup[vid] = v

        # Average metrics per variant
        variant_metrics: dict[str, dict[str, list[float]]] = {}
        for entry in metrics_list:
            vid = entry.get("variant_id", "unknown")
            mtype = entry.get("metric_type") or entry.get("type") or entry.get("name")
            value = entry.get("value")
            if mtype is None or value is None:
                continue
            variant_metrics.setdefault(vid, {}).setdefault(mtype.lower().strip(), []).append(float(value))

        for vid, m_dict in variant_metrics.items():
            variant_info = variant_lookup.get(vid, {})
            averaged = {}
            for mtype, values in m_dict.items():
                averaged[mtype] = sum(values) / len(values)

            all_variant_data.append({
                "campaign_id": campaign_id,
                "variant_id": vid,
                "channel": camp_channel,
                "tone": variant_info.get("tone", "").lower().strip(),
                "cta": (variant_info.get("cta") or variant_info.get("call_to_action", "")).lower().strip(),
                "subject_line": variant_info.get("subject_line", ""),
                "metrics": averaged,
            })

    # ------------------------------------------------------------------
    # Check minimum campaign threshold
    # ------------------------------------------------------------------
    if campaign_count < min_campaigns:
        return (
            f"Not enough campaigns to identify patterns. "
            f"Found {campaign_count} campaign(s) with metrics for channel='{channel}', "
            f"but need at least {min_campaigns}. "
            f"Run more campaigns and log metrics first."
        )

    if not all_variant_data:
        return "No variant data with metrics found across campaigns."

    # ------------------------------------------------------------------
    # Group by attributes and compare metrics
    # ------------------------------------------------------------------
    groupable_attrs = ["tone", "cta", "channel"]
    # Collect all metric types seen across all variants
    all_metric_types: set[str] = set()
    for vd in all_variant_data:
        all_metric_types.update(vd["metrics"].keys())

    patterns: list[dict] = []

    for attr in groupable_attrs:
        # Group variants by attribute value
        groups: dict[str, list[dict]] = {}
        for vd in all_variant_data:
            attr_val = vd.get(attr, "")
            if not attr_val:
                continue
            groups.setdefault(attr_val, []).append(vd)

        # Need at least 2 distinct values to compare
        if len(groups) < 2:
            continue

        # For each metric, compare averages across groups
        for mtype in sorted(all_metric_types):
            group_avgs: dict[str, tuple[float, int]] = {}  # value -> (avg, count)
            for attr_val, variants in groups.items():
                values = [v["metrics"][mtype] for v in variants if mtype in v["metrics"]]
                if values:
                    group_avgs[attr_val] = (sum(values) / len(values), len(values))

            if len(group_avgs) < 2:
                continue

            # Find best and worst performers
            positive = _metric_is_positive(mtype)
            sorted_groups = sorted(
                group_avgs.items(),
                key=lambda x: x[1][0],
                reverse=positive,
            )

            best_name, (best_avg, best_count) = sorted_groups[0]
            worst_name, (worst_avg, worst_count) = sorted_groups[-1]

            # Only report if there is a meaningful difference (>10%)
            if worst_avg == 0 and best_avg == 0:
                continue
            if worst_avg != 0:
                pct_diff = abs(best_avg - worst_avg) / abs(worst_avg) * 100
            else:
                pct_diff = 100.0

            if pct_diff < 10:
                continue

            patterns.append({
                "attribute": attr,
                "metric": mtype,
                "best_value": best_name,
                "best_avg": best_avg,
                "best_sample": best_count,
                "worst_value": worst_name,
                "worst_avg": worst_avg,
                "worst_sample": worst_count,
                "pct_diff": pct_diff,
                "direction": "higher is better" if positive else "lower is better",
            })

    # ------------------------------------------------------------------
    # Also check subject line patterns (questions, numbers, length)
    # ------------------------------------------------------------------
    email_variants = [vd for vd in all_variant_data if vd.get("subject_line")]
    if len(email_variants) >= 2:
        # Question vs non-question subject lines
        question_group: list[dict] = []
        non_question_group: list[dict] = []
        for vd in email_variants:
            if "?" in vd["subject_line"]:
                question_group.append(vd)
            else:
                non_question_group.append(vd)

        if question_group and non_question_group:
            for mtype in sorted(all_metric_types):
                q_vals = [v["metrics"][mtype] for v in question_group if mtype in v["metrics"]]
                nq_vals = [v["metrics"][mtype] for v in non_question_group if mtype in v["metrics"]]
                if q_vals and nq_vals:
                    q_avg = sum(q_vals) / len(q_vals)
                    nq_avg = sum(nq_vals) / len(nq_vals)
                    if nq_avg != 0:
                        pct = abs(q_avg - nq_avg) / abs(nq_avg) * 100
                    elif q_avg != 0:
                        pct = 100.0
                    else:
                        pct = 0.0
                    if pct >= 10:
                        positive = _metric_is_positive(mtype)
                        better = "question" if (q_avg > nq_avg) == positive else "non-question"
                        patterns.append({
                            "attribute": "subject_format",
                            "metric": mtype,
                            "best_value": better,
                            "best_avg": q_avg if better == "question" else nq_avg,
                            "best_sample": len(q_vals) if better == "question" else len(nq_vals),
                            "worst_value": "non-question" if better == "question" else "question",
                            "worst_avg": nq_avg if better == "question" else q_avg,
                            "worst_sample": len(nq_vals) if better == "question" else len(q_vals),
                            "pct_diff": pct,
                            "direction": "higher is better" if positive else "lower is better",
                        })

        # Short vs long subject lines (threshold: 50 chars)
        short_group = [vd for vd in email_variants if len(vd["subject_line"]) < 50]
        long_group = [vd for vd in email_variants if len(vd["subject_line"]) >= 50]
        if short_group and long_group:
            for mtype in sorted(all_metric_types):
                s_vals = [v["metrics"][mtype] for v in short_group if mtype in v["metrics"]]
                l_vals = [v["metrics"][mtype] for v in long_group if mtype in v["metrics"]]
                if s_vals and l_vals:
                    s_avg = sum(s_vals) / len(s_vals)
                    l_avg = sum(l_vals) / len(l_vals)
                    if l_avg != 0:
                        pct = abs(s_avg - l_avg) / abs(l_avg) * 100
                    elif s_avg != 0:
                        pct = 100.0
                    else:
                        pct = 0.0
                    if pct >= 10:
                        positive = _metric_is_positive(mtype)
                        better = "short (<50 chars)" if (s_avg > l_avg) == positive else "long (50+ chars)"
                        patterns.append({
                            "attribute": "subject_length",
                            "metric": mtype,
                            "best_value": better,
                            "best_avg": s_avg if "short" in better else l_avg,
                            "best_sample": len(s_vals) if "short" in better else len(l_vals),
                            "worst_value": "long (50+ chars)" if "short" in better else "short (<50 chars)",
                            "worst_avg": l_avg if "short" in better else s_avg,
                            "worst_sample": len(l_vals) if "short" in better else len(s_vals),
                            "pct_diff": pct,
                            "direction": "higher is better" if positive else "lower is better",
                        })

    # ------------------------------------------------------------------
    # Build the report
    # ------------------------------------------------------------------
    lines = [
        "=" * 60,
        "CROSS-CAMPAIGN PATTERN ANALYSIS",
        "=" * 60,
        "",
        f"Campaigns analyzed: {campaign_count}",
        f"Total variants with metrics: {len(all_variant_data)}",
        f"Channel filter: {channel}",
        "",
    ]

    if not patterns:
        lines.append("No statistically meaningful patterns found (>10% difference).")
        lines.append("This could mean:")
        lines.append("  - Not enough data points yet")
        lines.append("  - Variants are too similar in attributes")
        lines.append("  - Performance is consistent across different approaches")
        lines.append("")
        lines.append("Try running more campaigns with distinct attribute variations.")
    else:
        # Sort patterns by pct_diff descending (most impactful first)
        patterns.sort(key=lambda p: p["pct_diff"], reverse=True)

        lines.append(f"Patterns found: {len(patterns)}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("PATTERNS (sorted by impact)")
        lines.append("-" * 60)
        lines.append("")

        for i, p in enumerate(patterns, 1):
            lines.append(
                f"  {i}. {p['attribute'].upper()} -> {p['metric']}"
            )
            lines.append(
                f"     Best: \"{p['best_value']}\" avg {_format_value(p['best_avg'])} "
                f"(n={p['best_sample']})"
            )
            lines.append(
                f"     Worst: \"{p['worst_value']}\" avg {_format_value(p['worst_avg'])} "
                f"(n={p['worst_sample']})"
            )
            lines.append(
                f"     Difference: {p['pct_diff']:.1f}% ({p['direction']})"
            )
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 6: get_recommendations
# ---------------------------------------------------------------------------

@function_tool
def get_recommendations(
    channel: str,
    brief: str = "",
) -> str:
    """Generate data-driven copy recommendations based on playbook learnings and campaign patterns.

    Reads the playbook for the specified channel, analyzes recent campaign performance,
    and cross-references with identified patterns. Returns a prioritized list of
    recommendations with confidence levels and supporting evidence.

    Args:
        channel: The target channel — one of: email, sms, seo, ad.
        brief: Optional campaign brief for context-aware recommendations.
    """
    valid_channels = {"email", "sms", "seo", "ad"}
    channel_lower = channel.lower().strip()
    if channel_lower not in valid_channels:
        return f"Invalid channel '{channel}'. Must be one of: {', '.join(sorted(valid_channels))}"

    recommendations: list[dict] = []

    # ------------------------------------------------------------------
    # 1. Read playbook learnings for this channel (and general)
    # ------------------------------------------------------------------
    playbook_path = DATA_DIR / "playbook.json"
    lock_path = playbook_path.with_suffix(".json.lock")

    playbook_learnings: list[dict] = []
    with FileLock(lock_path):
        data = _load_json(playbook_path)

    if data and data.get("learnings"):
        for entry in data["learnings"]:
            # Skip deactivated learnings
            if entry.get("deactivated"):
                continue
            cat = entry.get("category", "general")
            if cat == channel_lower or cat == "general":
                playbook_learnings.append(entry)

    # Convert high-confidence playbook learnings into recommendations
    for entry in playbook_learnings:
        conf = entry.get("confidence", 0.3)
        confirmed = entry.get("times_confirmed", 0)

        # Determine recommendation strength
        if conf >= 0.9:
            confidence_label = "HIGH"
        elif conf >= 0.6:
            confidence_label = "MEDIUM"
        else:
            confidence_label = "LOW"

        evidence_parts = []
        if entry.get("evidence"):
            evidence_parts.append(entry["evidence"])
        if confirmed > 0:
            evidence_parts.append(f"confirmed {confirmed}x across campaigns")
        if entry.get("source") == "seed" and confirmed == 0:
            evidence_parts.append("industry best practice (not yet confirmed by your data)")

        recommendations.append({
            "recommendation": entry["learning"],
            "confidence": confidence_label,
            "confidence_value": conf,
            "evidence": "; ".join(evidence_parts) if evidence_parts else "playbook entry",
            "source": "playbook",
            "confirmed_count": confirmed,
        })

    # ------------------------------------------------------------------
    # 2. Scan recent campaigns for performance insights
    # ------------------------------------------------------------------
    campaigns_dir = DATA_DIR / "campaigns"

    if campaigns_dir.exists():
        # Collect all variant data for this channel
        all_variants: list[dict] = []
        campaign_names: list[str] = []

        for campaign_path in campaigns_dir.iterdir():
            if not campaign_path.is_dir():
                continue

            brief_path = campaign_path / "brief.json"
            variants_path = campaign_path / "variants.json"
            metrics_path = campaign_path / "metrics.json"

            if not brief_path.exists() or not metrics_path.exists():
                continue

            brief_data = _load_json(brief_path)
            if brief_data is None:
                continue

            camp_channel = brief_data.get("channel", "unknown").lower()
            if camp_channel != channel_lower:
                continue

            variants_data = _load_json(variants_path)
            metrics_data = _load_json(metrics_path)
            if not variants_data or not metrics_data:
                continue

            variants_list = variants_data if isinstance(variants_data, list) else variants_data.get("variants", [])
            metrics_list = metrics_data if isinstance(metrics_data, list) else metrics_data.get("metrics", [])
            if not metrics_list:
                continue

            campaign_id = brief_data.get("campaign_id", campaign_path.name)
            campaign_names.append(campaign_id)

            # Build variant lookup
            variant_lookup: dict[str, dict] = {}
            for v in variants_list:
                vid = v.get("variant_id") or v.get("id")
                if vid:
                    variant_lookup[vid] = v

            # Average metrics per variant
            variant_metrics: dict[str, dict[str, list[float]]] = {}
            for entry in metrics_list:
                vid = entry.get("variant_id", "unknown")
                mtype = entry.get("metric_type") or entry.get("type") or entry.get("name")
                value = entry.get("value")
                if mtype is None or value is None:
                    continue
                variant_metrics.setdefault(vid, {}).setdefault(mtype.lower().strip(), []).append(float(value))

            for vid, m_dict in variant_metrics.items():
                variant_info = variant_lookup.get(vid, {})
                averaged = {}
                for mtype, values in m_dict.items():
                    averaged[mtype] = sum(values) / len(values)

                all_variants.append({
                    "campaign_id": campaign_id,
                    "variant_id": vid,
                    "tone": variant_info.get("tone", "").lower().strip(),
                    "cta": (variant_info.get("cta") or variant_info.get("call_to_action", "")).lower().strip(),
                    "subject_line": variant_info.get("subject_line", ""),
                    "metrics": averaged,
                })

        # ------------------------------------------------------------------
        # Find the best-performing attributes from campaign data
        # ------------------------------------------------------------------
        if len(campaign_names) >= 1 and all_variants:
            # Group by tone
            tone_groups: dict[str, list[dict]] = {}
            for vd in all_variants:
                if vd["tone"]:
                    tone_groups.setdefault(vd["tone"], []).append(vd)

            # Group by CTA
            cta_groups: dict[str, list[dict]] = {}
            for vd in all_variants:
                if vd["cta"]:
                    cta_groups.setdefault(vd["cta"], []).append(vd)

            # Generate insights from groups with enough data
            for attr_name, groups in [("tone", tone_groups), ("CTA style", cta_groups)]:
                if len(groups) < 2:
                    continue

                # Collect all metrics seen
                metric_types = set()
                for variants in groups.values():
                    for v in variants:
                        metric_types.update(v["metrics"].keys())

                for mtype in sorted(metric_types):
                    group_avgs: list[tuple[str, float, int]] = []
                    for attr_val, variants in groups.items():
                        vals = [v["metrics"][mtype] for v in variants if mtype in v["metrics"]]
                        if vals:
                            group_avgs.append((attr_val, sum(vals) / len(vals), len(vals)))

                    if len(group_avgs) < 2:
                        continue

                    positive = _metric_is_positive(mtype)
                    group_avgs.sort(key=lambda x: x[1], reverse=positive)

                    best_name, best_avg, best_count = group_avgs[0]
                    worst_name, worst_avg, worst_count = group_avgs[-1]

                    if worst_avg != 0:
                        pct = abs(best_avg - worst_avg) / abs(worst_avg) * 100
                    elif best_avg != 0:
                        pct = 100.0
                    else:
                        continue

                    if pct < 5:
                        continue

                    total_data_points = sum(g[2] for g in group_avgs)
                    conf_label = "HIGH" if total_data_points >= 6 else "MEDIUM" if total_data_points >= 3 else "LOW"
                    conf_value = 0.9 if conf_label == "HIGH" else 0.6 if conf_label == "MEDIUM" else 0.3

                    rec_text = (
                        f"Based on {len(campaign_names)} campaign(s), use {attr_name}=\"{best_name}\" "
                        f"(avg {_format_value(best_avg)} {mtype}) over \"{worst_name}\" "
                        f"(avg {_format_value(worst_avg)} {mtype}) — "
                        f"{pct:.0f}% {'better' if positive else 'lower (better)'}."
                    )

                    recommendations.append({
                        "recommendation": rec_text,
                        "confidence": conf_label,
                        "confidence_value": conf_value,
                        "evidence": f"Data from {len(campaign_names)} campaign(s): {', '.join(campaign_names[:5])}",
                        "source": "campaign_data",
                        "confirmed_count": total_data_points,
                    })

    # ------------------------------------------------------------------
    # 3. Deduplicate and prioritize recommendations
    # ------------------------------------------------------------------
    # Sort: campaign_data first (empirical), then playbook; within each, by confidence desc
    source_priority = {"campaign_data": 0, "playbook": 1}
    recommendations.sort(
        key=lambda r: (source_priority.get(r["source"], 2), -r["confidence_value"], -r.get("confirmed_count", 0))
    )

    # Remove exact duplicate recommendations
    seen_recs: set[str] = set()
    unique_recs: list[dict] = []
    for rec in recommendations:
        rec_lower = rec["recommendation"].lower()[:80]
        if rec_lower not in seen_recs:
            seen_recs.add(rec_lower)
            unique_recs.append(rec)

    # ------------------------------------------------------------------
    # 4. Build the report
    # ------------------------------------------------------------------
    lines = [
        "=" * 60,
        f"COPY RECOMMENDATIONS: {channel_lower.upper()}",
        "=" * 60,
        "",
    ]

    if brief:
        lines.append(f"Brief context: {brief[:200]}")
        lines.append("")

    if not unique_recs:
        lines.append("No recommendations available yet.")
        lines.append("")
        lines.append("To build recommendations:")
        lines.append("  1. Create campaigns with generate_copy")
        lines.append("  2. Log metrics with log_metrics")
        lines.append("  3. Save learnings with save_learning")
        lines.append("  4. Re-run get_recommendations")
    else:
        # Split into data-driven and playbook sections
        data_recs = [r for r in unique_recs if r["source"] == "campaign_data"]
        playbook_recs = [r for r in unique_recs if r["source"] == "playbook"]

        if data_recs:
            lines.append("-" * 60)
            lines.append("DATA-DRIVEN RECOMMENDATIONS (from your campaigns)")
            lines.append("-" * 60)
            lines.append("")
            for i, rec in enumerate(data_recs, 1):
                lines.append(f"  {i}. [{rec['confidence']}] {rec['recommendation']}")
                lines.append(f"     Evidence: {rec['evidence']}")
                lines.append("")

        if playbook_recs:
            lines.append("-" * 60)
            lines.append("PLAYBOOK RECOMMENDATIONS (learnings library)")
            lines.append("-" * 60)
            lines.append("")

            # Show high-confidence first, then medium, then low
            high = [r for r in playbook_recs if r["confidence"] == "HIGH"]
            medium = [r for r in playbook_recs if r["confidence"] == "MEDIUM"]
            low = [r for r in playbook_recs if r["confidence"] == "LOW"]

            counter = 1
            for group, label in [(high, "HIGH"), (medium, "MEDIUM"), (low, "LOW")]:
                if not group:
                    continue
                for rec in group:
                    lines.append(f"  {counter}. [{rec['confidence']}] {rec['recommendation']}")
                    lines.append(f"     Evidence: {rec['evidence']}")
                    lines.append("")
                    counter += 1

        lines.append("-" * 60)
        lines.append(f"Total recommendations: {len(unique_recs)} "
                     f"({len(data_recs)} data-driven, {len(playbook_recs)} from playbook)")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
