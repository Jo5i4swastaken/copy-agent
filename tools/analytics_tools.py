"""
Advanced analytics and reporting tools for the Copy Agent (Phase 4).

Provides trend computation, anomaly detection, and structured report
generation across campaigns and channels.
"""

import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from tools.lock import FileLock
from omniagents import function_tool

from tools.stats import detect_anomaly

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CAMPAIGNS_DIR = DATA_DIR / "campaigns"
PLAYBOOK_PATH = DATA_DIR / "playbook.json"
REPORTS_DIR = DATA_DIR / "reports"

VALID_REPORT_TYPES = {
    "campaign_performance",
    "channel_trends",
    "cross_channel_insights",
    "playbook_health",
    "anomaly_alerts",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def _collect_metrics_for_channel(channel: str) -> list[dict]:
    """Gather all metrics entries from campaigns in a given channel."""
    if not CAMPAIGNS_DIR.exists():
        return []

    all_metrics = []
    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue
        brief = _load_json(campaign_dir / "brief.json")
        if brief is None or brief.get("channel") != channel:
            continue
        metrics_path = campaign_dir / "metrics.json"
        metrics = _load_json(metrics_path)
        if isinstance(metrics, list):
            for m in metrics:
                m["campaign_id"] = brief.get("campaign_id", campaign_dir.name)
            all_metrics.extend(metrics)
    return all_metrics


def _collect_all_metrics() -> list[dict]:
    """Gather all metrics from all campaigns."""
    if not CAMPAIGNS_DIR.exists():
        return []

    all_metrics = []
    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue
        brief = _load_json(campaign_dir / "brief.json") or {}
        metrics = _load_json(campaign_dir / "metrics.json")
        if isinstance(metrics, list):
            for m in metrics:
                m["campaign_id"] = brief.get("campaign_id", campaign_dir.name)
                m["channel"] = brief.get("channel", "unknown")
            all_metrics.extend(metrics)
    return all_metrics


# ---------------------------------------------------------------------------
# Tool 1: compute_trends
# ---------------------------------------------------------------------------

@function_tool
def compute_trends(channel: str, metric: str, days: int = 30) -> str:
    """Compute rolling average trends for a metric across a channel.

    Aggregates metrics data from all campaigns in the specified channel,
    computes daily averages and a rolling 7-day average, and reports
    period-over-period change.

    Args:
        channel: The channel to analyze (email, sms, ad, seo).
        metric: The metric name (e.g. open_rate, click_rate, ctr).
        days: Number of days to look back (default 30).

    Returns:
        Formatted trend analysis with rolling averages and direction.
    """
    all_metrics = _collect_metrics_for_channel(channel)
    if not all_metrics:
        return f"No metrics data found for channel '{channel}'."

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    # Filter to relevant metric entries within the time window
    relevant = []
    for m in all_metrics:
        logged_at = m.get("logged_at", m.get("date", ""))
        if logged_at < cutoff:
            continue
        value = m.get(metric) or m.get("value")
        if isinstance(value, (int, float)):
            relevant.append({"date": logged_at[:10], "value": value})

    if not relevant:
        return f"No '{metric}' data found for channel '{channel}' in the last {days} days."

    # Group by day
    by_day: dict[str, list[float]] = defaultdict(list)
    for entry in relevant:
        by_day[entry["date"]].append(entry["value"])

    daily_avgs = {d: sum(vs) / len(vs) for d, vs in sorted(by_day.items())}
    sorted_days = sorted(daily_avgs.keys())
    values = [daily_avgs[d] for d in sorted_days]

    # Overall stats
    overall_avg = sum(values) / len(values) if values else 0
    latest = values[-1] if values else 0

    # Rolling 7-day average
    rolling_7d = []
    for i in range(len(values)):
        window = values[max(0, i - 6):i + 1]
        rolling_7d.append(sum(window) / len(window))

    # Period-over-period change
    if len(values) >= 2:
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)
        if first_half > 0:
            change_pct = ((second_half - first_half) / first_half) * 100
        else:
            change_pct = 0
    else:
        change_pct = 0

    direction = "improving" if change_pct > 2 else ("declining" if change_pct < -2 else "stable")

    lines = [
        "=" * 60,
        f"TREND ANALYSIS: {channel}/{metric} ({days} days)",
        "=" * 60,
        f"Data points: {len(relevant)} across {len(sorted_days)} days",
        f"Overall average: {overall_avg:.4f}",
        f"Latest value: {latest:.4f}",
        f"Period-over-period change: {change_pct:+.1f}%",
        f"Direction: {direction.upper()}",
        "",
        "Rolling 7-day averages (last 10 days):",
    ]

    for i in range(max(0, len(sorted_days) - 10), len(sorted_days)):
        lines.append(f"  {sorted_days[i]}: {rolling_7d[i]:.4f}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: detect_anomalies
# ---------------------------------------------------------------------------

@function_tool
def detect_anomalies(channel: str, metric: str, threshold: float = 2.0) -> str:
    """Detect anomalous metric values for a channel using z-score analysis.

    Compares recent metric values against historical averages to identify
    unusual spikes or drops that may need investigation.

    Args:
        channel: The channel to check (email, sms, ad, seo).
        metric: The metric name to analyze.
        threshold: Z-score threshold for anomaly detection (default 2.0).

    Returns:
        List of detected anomalies or confirmation that metrics are normal.
    """
    all_metrics = _collect_metrics_for_channel(channel)
    if not all_metrics:
        return f"No metrics data found for channel '{channel}'."

    # Extract values for the metric, sorted by date
    entries = []
    for m in all_metrics:
        value = m.get(metric) or m.get("value")
        logged_at = m.get("logged_at", m.get("date", ""))
        if isinstance(value, (int, float)) and logged_at:
            entries.append({"value": value, "date": logged_at, "campaign_id": m.get("campaign_id", "")})

    entries.sort(key=lambda e: e["date"])

    if len(entries) < 6:
        return f"Not enough data points ({len(entries)}) for anomaly detection. Need at least 6."

    # Check the most recent 5 entries against the historical baseline
    historical = [e["value"] for e in entries[:-5]]
    recent = entries[-5:]
    anomalies = []

    for entry in recent:
        result = detect_anomaly(entry["value"], historical, threshold)
        if result is not None:
            anomalies.append({
                "date": entry["date"],
                "campaign_id": entry["campaign_id"],
                "channel": channel,
                "metric": metric,
                **result,
            })

    if not anomalies:
        return (
            f"No anomalies detected for {channel}/{metric}. "
            f"All recent values are within {threshold}σ of the historical mean."
        )

    lines = [
        "=" * 60,
        f"ANOMALY DETECTION: {channel}/{metric}",
        "=" * 60,
        f"Anomalies found: {len(anomalies)}",
        "",
    ]

    for a in anomalies:
        lines.append(f"  [{a['direction'].upper()}] {a['date']}")
        lines.append(f"    Value: {a['value']:.4f} (z-score: {a['z_score']:.2f})")
        lines.append(f"    Expected range: {a['expected_range'][0]:.4f} – {a['expected_range'][1]:.4f}")
        lines.append(f"    Campaign: {a['campaign_id']}")
        lines.append("")

    lines.append("Investigate these campaigns for unusual conditions or data issues.")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 3: generate_report
# ---------------------------------------------------------------------------

@function_tool
def generate_report(report_type: str, campaign_id: str = "", channel: str = "") -> str:
    """Generate a structured analytics report.

    Available report types:
    - campaign_performance: Deep dive on a specific campaign
    - channel_trends: Performance trends across a channel
    - cross_channel_insights: Patterns spanning multiple channels
    - playbook_health: Confidence distribution, stale learnings, gaps
    - anomaly_alerts: Recent unusual metric changes

    Args:
        report_type: One of the valid report types above.
        campaign_id: Required for campaign_performance reports.
        channel: Required for channel_trends reports.

    Returns:
        Formatted report content and confirmation of save.
    """
    if report_type not in VALID_REPORT_TYPES:
        return (
            f"Error: Invalid report type '{report_type}'. "
            f"Valid types: {', '.join(sorted(VALID_REPORT_TYPES))}."
        )

    now = datetime.now()
    report_id = f"report-{report_type}-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    if report_type == "campaign_performance":
        content = _report_campaign_performance(campaign_id)
    elif report_type == "channel_trends":
        content = _report_channel_trends(channel)
    elif report_type == "cross_channel_insights":
        content = _report_cross_channel_insights()
    elif report_type == "playbook_health":
        content = _report_playbook_health()
    elif report_type == "anomaly_alerts":
        content = _report_anomaly_alerts()
    else:
        content = {"error": f"Unhandled report type: {report_type}"}

    report = {
        "report_id": report_id,
        "report_type": report_type,
        "generated_at": now.isoformat(),
        "parameters": {"campaign_id": campaign_id, "channel": channel},
        "content": content,
    }

    _save_json(REPORTS_DIR / f"{report_id}.json", report)

    # Format for display
    lines = [
        "=" * 60,
        f"REPORT: {report_type.upper().replace('_', ' ')}",
        f"ID: {report_id}",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "",
    ]

    if isinstance(content, dict):
        if "error" in content:
            lines.append(f"Error: {content['error']}")
        else:
            lines.append(json.dumps(content, indent=2, default=str))
    else:
        lines.append(str(content))

    lines.append("")
    lines.append(f"Report saved. Use get_report('{report_id}') to retrieve it later.")
    lines.append("=" * 60)

    return "\n".join(lines)


def _report_campaign_performance(campaign_id: str) -> dict:
    if not campaign_id:
        return {"error": "campaign_id is required for campaign_performance reports."}

    campaign_dir = CAMPAIGNS_DIR / campaign_id
    brief = _load_json(campaign_dir / "brief.json")
    if brief is None:
        return {"error": f"Campaign '{campaign_id}' not found."}

    variants = _load_json(campaign_dir / "variants.json") or []
    metrics = _load_json(campaign_dir / "metrics.json") or []
    ab_state = _load_json(campaign_dir / "ab_test_state.json")

    # Aggregate metrics per variant
    variant_metrics: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for m in metrics:
        vid = m.get("variant_id", "unknown")
        for k, v in m.items():
            if isinstance(v, (int, float)) and k not in ("variant_id",):
                variant_metrics[vid][k].append(v)

    variant_summaries = {}
    for vid, metric_dict in variant_metrics.items():
        summary = {}
        for metric_name, values in metric_dict.items():
            summary[metric_name] = {
                "avg": round(sum(values) / len(values), 4),
                "count": len(values),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
            }
        variant_summaries[vid] = summary

    return {
        "campaign_id": campaign_id,
        "channel": brief.get("channel", "unknown"),
        "status": brief.get("status", "unknown"),
        "total_variants": len(variants),
        "total_metric_entries": len(metrics),
        "variant_performance": variant_summaries,
        "ab_test_active": ab_state is not None,
        "ab_test_state": ab_state.get("state") if ab_state else None,
    }


def _report_channel_trends(channel: str) -> dict:
    if not channel:
        return {"error": "channel is required for channel_trends reports."}

    all_metrics = _collect_metrics_for_channel(channel)
    if not all_metrics:
        return {"channel": channel, "message": "No metrics data found.", "trends": {}}

    # Aggregate all metrics by name
    by_metric: dict[str, list[float]] = defaultdict(list)
    for m in all_metrics:
        for k, v in m.items():
            if isinstance(v, (int, float)) and k not in ("campaign_id", "variant_id"):
                by_metric[k].append(v)

    trends = {}
    for metric_name, values in by_metric.items():
        if len(values) < 2:
            continue
        avg = sum(values) / len(values)
        trends[metric_name] = {
            "avg": round(avg, 4),
            "count": len(values),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }

    return {"channel": channel, "metrics_tracked": len(trends), "trends": trends}


def _report_cross_channel_insights() -> dict:
    all_metrics = _collect_all_metrics()
    if not all_metrics:
        return {"message": "No metrics data found."}

    # Group by channel, then metric
    by_channel: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for m in all_metrics:
        ch = m.get("channel", "unknown")
        for k, v in m.items():
            if isinstance(v, (int, float)) and k not in ("campaign_id", "variant_id", "channel"):
                by_channel[ch][k].append(v)

    channel_avgs: dict[str, dict[str, float]] = {}
    for ch, metrics in by_channel.items():
        channel_avgs[ch] = {}
        for metric_name, values in metrics.items():
            if values:
                channel_avgs[ch][metric_name] = round(sum(values) / len(values), 4)

    # Find shared metrics across channels for comparison
    all_metric_names = set()
    for metrics in channel_avgs.values():
        all_metric_names.update(metrics.keys())

    shared_metrics = {}
    for metric_name in all_metric_names:
        channels_with = {ch: avgs[metric_name] for ch, avgs in channel_avgs.items() if metric_name in avgs}
        if len(channels_with) >= 2:
            shared_metrics[metric_name] = channels_with

    return {
        "channels_analyzed": list(channel_avgs.keys()),
        "channel_averages": channel_avgs,
        "cross_channel_comparisons": shared_metrics,
    }


def _report_playbook_health() -> dict:
    data = _load_json(PLAYBOOK_PATH)
    if data is None:
        return {"message": "No playbook found."}

    learnings = data.get("learnings", [])
    if not learnings:
        return {"message": "Playbook is empty."}

    total = len(learnings)
    by_confidence = {"high": 0, "medium": 0, "low": 0, "deactivated": 0}
    by_category: dict[str, int] = defaultdict(int)
    stale = []

    for l in learnings:
        conf = l.get("confidence", 0)
        if conf >= 0.8:
            by_confidence["high"] += 1
        elif conf >= 0.5:
            by_confidence["medium"] += 1
        elif conf > 0:
            by_confidence["low"] += 1
        else:
            by_confidence["deactivated"] += 1

        cat = l.get("category", "uncategorized")
        by_category[cat] += 1

        # Check for stale learnings (seed, never confirmed, old)
        if l.get("source") == "seed" and l.get("times_confirmed", 0) == 0:
            stale.append(l.get("id", l.get("learning", "")[:50]))

    return {
        "total_learnings": total,
        "by_confidence": by_confidence,
        "by_category": dict(by_category),
        "stale_seed_learnings": len(stale),
        "stale_ids": stale[:10],
    }


def _report_anomaly_alerts() -> dict:
    all_metrics = _collect_all_metrics()
    if not all_metrics:
        return {"anomalies": [], "message": "No metrics data."}

    # Group by channel+metric
    by_key: dict[str, list[dict]] = defaultdict(list)
    for m in all_metrics:
        ch = m.get("channel", "unknown")
        for k, v in m.items():
            if isinstance(v, (int, float)) and k not in ("campaign_id", "variant_id", "channel"):
                by_key[f"{ch}/{k}"].append({"value": v, "date": m.get("logged_at", ""), "campaign_id": m.get("campaign_id", "")})

    anomalies = []
    for key, entries in by_key.items():
        entries.sort(key=lambda e: e["date"])
        if len(entries) < 6:
            continue

        historical = [e["value"] for e in entries[:-3]]
        recent = entries[-3:]

        for entry in recent:
            result = detect_anomaly(entry["value"], historical)
            if result is not None:
                ch, metric = key.split("/", 1)
                anomalies.append({
                    "channel": ch,
                    "metric": metric,
                    "campaign_id": entry["campaign_id"],
                    "date": entry["date"],
                    **result,
                })

    return {
        "report_type": "anomaly_alerts",
        "anomalies_found": len(anomalies),
        "anomalies": anomalies[:20],
    }


# ---------------------------------------------------------------------------
# Tool 4: list_reports
# ---------------------------------------------------------------------------

@function_tool
def list_reports(report_type: str = "") -> str:
    """List all generated reports, optionally filtered by type.

    Args:
        report_type: Optional filter by report type. If empty, lists all.

    Returns:
        Formatted list of reports with ID, type, and generation date.
    """
    if not REPORTS_DIR.exists():
        return "No reports generated yet."

    reports = []
    for report_file in sorted(REPORTS_DIR.iterdir(), reverse=True):
        if report_file.suffix != ".json":
            continue
        data = _load_json(report_file)
        if data is None:
            continue
        if report_type and data.get("report_type") != report_type:
            continue
        reports.append({
            "report_id": data.get("report_id", report_file.stem),
            "report_type": data.get("report_type", "unknown"),
            "generated_at": data.get("generated_at", ""),
        })

    if not reports:
        filter_msg = f" of type '{report_type}'" if report_type else ""
        return f"No reports{filter_msg} found."

    lines = [
        "=" * 60,
        f"REPORTS ({len(reports)})",
        "=" * 60,
        "",
    ]

    for r in reports[:20]:
        lines.append(f"  {r['report_id']}")
        lines.append(f"    Type: {r['report_type']} | Generated: {r['generated_at']}")
        lines.append("")

    lines.append("Use get_report(report_id) to read a specific report.")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 5: get_report
# ---------------------------------------------------------------------------

@function_tool
def get_report(report_id: str) -> str:
    """Retrieve a specific generated report.

    Args:
        report_id: The ID of the report to retrieve.

    Returns:
        The full report content.
    """
    report_path = REPORTS_DIR / f"{report_id}.json"
    data = _load_json(report_path)
    if data is None:
        return f"Error: Report '{report_id}' not found."

    lines = [
        "=" * 60,
        f"REPORT: {data.get('report_type', 'unknown').upper().replace('_', ' ')}",
        f"ID: {report_id}",
        f"Generated: {data.get('generated_at', 'unknown')}",
        "=" * 60,
        "",
        json.dumps(data.get("content", {}), indent=2, default=str),
        "",
        "=" * 60,
    ]

    return "\n".join(lines)
