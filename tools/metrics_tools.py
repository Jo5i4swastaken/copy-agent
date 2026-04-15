"""
Metrics tools for tracking and analyzing campaign performance.

Provides tools to log performance metrics per variant and retrieve
them for comparison across variants within a campaign.
"""

import json
from datetime import date, datetime
from pathlib import Path

from filelock import FileLock
from omniagents import function_tool

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VALID_METRIC_TYPES = {
    "open_rate",
    "click_rate",
    "reply_rate",
    "conversion_rate",
    "unsubscribe_rate",
    "impressions",
    "clicks",
    "ctr",
    "cost_per_click",
    "roas",
    "bounce_rate",
    "time_on_page",
    "search_position",
    "delivery_rate",
    "opt_out_rate",
}


def _campaign_dir(campaign_id: str) -> Path:
    """Return the directory for a given campaign."""
    return DATA_DIR / "campaigns" / campaign_id


def _metrics_path(campaign_id: str) -> Path:
    """Return the path to a campaign's metrics.json file."""
    return _campaign_dir(campaign_id) / "metrics.json"


def _lock_path(campaign_id: str) -> Path:
    """Return the path to the filelock for a campaign's metrics file."""
    return _campaign_dir(campaign_id) / "metrics.json.lock"


def _load_metrics(campaign_id: str) -> list[dict]:
    """Load existing metrics from disk, returning an empty list if none exist."""
    path = _metrics_path(campaign_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_metrics(campaign_id: str, metrics: list[dict]) -> None:
    """Persist the metrics list to disk with filelock protection."""
    path = _metrics_path(campaign_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(_lock_path(campaign_id)))
    with lock:
        path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")


def _campaign_exists(campaign_id: str) -> bool:
    """Check whether a campaign exists by looking for its brief.json."""
    return (_campaign_dir(campaign_id) / "brief.json").exists()


@function_tool
def log_metrics(
    campaign_id: str,
    variant_id: str,
    metric_type: str,
    value: float,
    date: str = "",
    notes: str = "",
) -> str:
    """Record a performance metric data point for a specific campaign variant.

    Parameters:
        campaign_id: The unique identifier of the campaign.
        variant_id: The identifier of the variant being measured (e.g. 'A', 'B', 'subject-line-v2').
        metric_type: The kind of metric. Must be one of: open_rate, click_rate, reply_rate,
            conversion_rate, unsubscribe_rate, impressions, clicks, ctr, cost_per_click,
            roas, bounce_rate, time_on_page, search_position, delivery_rate, opt_out_rate.
        value: The numeric value of the metric.
        date: The date the metric applies to in YYYY-MM-DD format. Defaults to today.
        notes: Optional free-text notes about this data point.
    """
    # Validate campaign exists
    if not _campaign_exists(campaign_id):
        return (
            f"Error: Campaign '{campaign_id}' not found. "
            "No brief.json exists for this campaign."
        )

    # Validate metric type
    if metric_type not in VALID_METRIC_TYPES:
        sorted_types = ", ".join(sorted(VALID_METRIC_TYPES))
        return (
            f"Error: Invalid metric_type '{metric_type}'. "
            f"Must be one of: {sorted_types}"
        )

    # Default date to today if not provided
    metric_date = date if date else datetime.now().strftime("%Y-%m-%d")

    # Build the metric entry
    entry = {
        "variant_id": variant_id,
        "metric_type": metric_type,
        "value": value,
        "date": metric_date,
        "notes": notes,
        "logged_at": datetime.now().isoformat(),
    }

    # Load, append, save with lock
    lock = FileLock(str(_lock_path(campaign_id)))
    with lock:
        metrics = _load_metrics(campaign_id)
        metrics.append(entry)
        path = _metrics_path(campaign_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")

    return (
        f"Logged {metric_type}={value} for variant '{variant_id}' "
        f"in campaign '{campaign_id}'"
    )


@function_tool
def get_variant_metrics(campaign_id: str, variant_id: str = "") -> str:
    """Retrieve performance metrics for a campaign, optionally filtered to a single variant.

    If variant_id is provided, returns only that variant's metrics. If omitted or empty,
    returns a comparison table of the latest metrics across all variants side by side.

    Parameters:
        campaign_id: The unique identifier of the campaign.
        variant_id: Optional. If provided, filter results to this variant only.
    """
    # Validate campaign exists
    if not _campaign_exists(campaign_id):
        return (
            f"Error: Campaign '{campaign_id}' not found. "
            "No brief.json exists for this campaign."
        )

    metrics = _load_metrics(campaign_id)
    if not metrics:
        return f"No metrics logged yet for campaign '{campaign_id}'"

    # -------------------------------------------------------------------
    # Single-variant view: return a detailed list of all data points
    # -------------------------------------------------------------------
    if variant_id:
        filtered = [m for m in metrics if m["variant_id"] == variant_id]
        if not filtered:
            return (
                f"No metrics found for variant '{variant_id}' "
                f"in campaign '{campaign_id}'"
            )

        lines = [
            f"Metrics for variant '{variant_id}' in campaign '{campaign_id}'",
            "=" * 60,
        ]

        # Group by metric type for readability
        by_type: dict[str, list[dict]] = {}
        for m in filtered:
            by_type.setdefault(m["metric_type"], []).append(m)

        for mtype in sorted(by_type.keys()):
            entries = sorted(by_type[mtype], key=lambda x: x["date"])
            lines.append(f"\n  {mtype}:")
            for e in entries:
                note_part = f"  ({e['notes']})" if e.get("notes") else ""
                lines.append(f"    {e['date']}  {e['value']}{note_part}")

        return "\n".join(lines)

    # -------------------------------------------------------------------
    # All-variants comparison: build a side-by-side table of latest values
    # -------------------------------------------------------------------

    # Collect the latest entry per (variant_id, metric_type)
    latest: dict[str, dict[str, dict]] = {}  # variant -> metric_type -> entry
    for m in metrics:
        vid = m["variant_id"]
        mtype = m["metric_type"]
        if vid not in latest:
            latest[vid] = {}
        existing = latest[vid].get(mtype)
        if existing is None or m["logged_at"] > existing["logged_at"]:
            latest[vid][mtype] = m

    variant_ids = sorted(latest.keys())
    all_metric_types = sorted(
        {mtype for v_metrics in latest.values() for mtype in v_metrics}
    )

    if not variant_ids or not all_metric_types:
        return f"No metrics logged yet for campaign '{campaign_id}'"

    # Build the comparison table
    # Column widths: metric_type label + one column per variant
    metric_col_width = max(len(mt) for mt in all_metric_types)
    metric_col_width = max(metric_col_width, len("Metric"))
    variant_col_width = 12

    # Header
    header = f"{'Metric':<{metric_col_width}}"
    for vid in variant_ids:
        header += f"  {vid:>{variant_col_width}}"
    separator = "-" * len(header)

    lines = [
        f"Campaign '{campaign_id}' - Variant Metrics Comparison",
        "=" * 60,
        "",
        header,
        separator,
    ]

    for mtype in all_metric_types:
        row = f"{mtype:<{metric_col_width}}"
        for vid in variant_ids:
            entry = latest[vid].get(mtype)
            if entry is not None:
                val = entry["value"]
                # Format as integer if whole number, otherwise 4 decimal places
                if val == int(val):
                    formatted = str(int(val))
                else:
                    formatted = f"{val:.4f}".rstrip("0").rstrip(".")
                row += f"  {formatted:>{variant_col_width}}"
            else:
                row += f"  {'--':>{variant_col_width}}"
        lines.append(row)

    lines.append(separator)
    lines.append(f"\nShowing latest value per metric. "
                 f"{len(metrics)} total data point(s) on record.")

    return "\n".join(lines)
