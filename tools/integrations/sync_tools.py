"""
OmniAgents tool wrappers that bridge the adapter pattern to the agent.

These @function_tool functions are what the agent actually calls. Each tool:
    1. Resolves the correct adapter from the registry.
    2. Delegates to the adapter's method.
    3. Auto-logs results to the campaign's metrics.json via the existing
       persistence helpers in metrics_tools.py.
    4. Returns a formatted string the agent can relay to the user.

The tools never import platform SDKs directly -- that is the adapter's job.
This keeps the tool layer thin and testable.
"""

import json
from datetime import datetime
from pathlib import Path

from filelock import FileLock
from omniagents import function_tool

from tools.integrations.registry import get_registry

# ---------------------------------------------------------------------------
# Paths -- consistent with copy_tools.py and metrics_tools.py
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data"
CAMPAIGNS_DIR: Path = DATA_DIR / "campaigns"


# ---------------------------------------------------------------------------
# Internal helpers (mirror the patterns in copy_tools.py / metrics_tools.py)
# ---------------------------------------------------------------------------

def _campaign_dir(campaign_id: str) -> Path:
    """Return the directory for a given campaign."""
    return CAMPAIGNS_DIR / campaign_id


def _campaign_exists(campaign_id: str) -> bool:
    """Check whether a campaign exists by looking for its brief.json."""
    return (_campaign_dir(campaign_id) / "brief.json").exists()


def _read_json(path: Path) -> dict | list:
    """Read and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict | list) -> None:
    """Write JSON atomically using a .lock file next to the target."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _append_metric(
    campaign_id: str,
    variant_id: str,
    metric_type: str,
    value: float,
    metric_date: str = "",
    notes: str = "",
) -> None:
    """Append a metric entry to a campaign's metrics.json.

    This mirrors the log_metrics tool's persistence logic so that
    metrics recorded through platform adapters appear in the same
    file and format as manually-logged metrics.
    """
    metrics_path = _campaign_dir(campaign_id) / "metrics.json"
    lock_path = metrics_path.with_suffix(metrics_path.suffix + ".lock")

    entry = {
        "variant_id": variant_id,
        "metric_type": metric_type,
        "value": value,
        "date": metric_date or datetime.now().strftime("%Y-%m-%d"),
        "notes": notes,
        "logged_at": datetime.now().isoformat(),
    }

    with FileLock(str(lock_path)):
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        else:
            metrics = []
        metrics.append(entry)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(
            json.dumps(metrics, indent=2, default=str),
            encoding="utf-8",
        )


def _log_send_record(
    campaign_id: str,
    variant_id: str,
    channel: str,
    send_result,
) -> None:
    """Persist a send record so the agent can correlate platform IDs
    back to campaign variants when fetching metrics later.

    Writes to data/campaigns/{campaign_id}/sends.json.
    """
    sends_path = _campaign_dir(campaign_id) / "sends.json"

    record = {
        "variant_id": variant_id,
        "channel": channel,
        "platform": send_result.platform,
        "platform_id": send_result.platform_id,
        "success": send_result.success,
        "sent_at": datetime.now().isoformat(),
        "error": send_result.error,
    }

    lock_path = sends_path.with_suffix(sends_path.suffix + ".lock")
    with FileLock(str(lock_path)):
        if sends_path.exists():
            sends = json.loads(sends_path.read_text(encoding="utf-8"))
        else:
            sends = []
        sends.append(record)
        sends_path.parent.mkdir(parents=True, exist_ok=True)
        sends_path.write_text(
            json.dumps(sends, indent=2, default=str),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@function_tool
def send_email(
    campaign_id: str,
    variant_id: str,
    to_emails: str,
    subject: str,
    content: str,
    from_email: str,
    reply_to: str = "",
    categories: str = "",
) -> str:
    """Send an email via the configured email platform (e.g. SendGrid).

    The platform_id returned by the adapter is logged to sends.json so
    metrics can be correlated back to this variant later.

    Args:
        campaign_id: The campaign this send belongs to.
        variant_id: The variant being sent (e.g. 'v1').
        to_emails: Comma-separated list of recipient email addresses.
        subject: Email subject line.
        content: HTML body content.
        from_email: Sender email address.
        reply_to: Optional reply-to address.
        categories: Optional comma-separated categories for tracking.
    """
    # Validate campaign
    if not _campaign_exists(campaign_id):
        return (
            f"Error: Campaign '{campaign_id}' not found. "
            "Create it with generate_copy first."
        )

    # Check adapter
    registry = get_registry()
    adapter = registry.get_email_adapter()
    if adapter is None:
        return (
            "Error: No email adapter configured. "
            "Set the SENDGRID_API_KEY environment variable to activate "
            "the SendGrid integration."
        )

    # Parse list inputs
    to_list = [e.strip() for e in to_emails.split(",") if e.strip()]
    if not to_list:
        return "Error: to_emails must contain at least one email address."

    cat_list = (
        [c.strip() for c in categories.split(",") if c.strip()]
        if categories
        else None
    )

    # Send
    result = adapter.send_email(
        to=to_list,
        subject=subject,
        html_content=content,
        from_email=from_email,
        reply_to=reply_to or None,
        categories=cat_list,
    )

    # Log the send record
    _log_send_record(campaign_id, variant_id, "email", result)

    if not result.success:
        return (
            f"Email send failed for variant '{variant_id}' "
            f"in campaign '{campaign_id}'.\n"
            f"Platform: {result.platform}\n"
            f"Error: {result.error}"
        )

    return (
        f"Email sent successfully.\n"
        f"Campaign: {campaign_id} | Variant: {variant_id}\n"
        f"Platform: {result.platform}\n"
        f"Platform ID: {result.platform_id}\n"
        f"Recipients: {len(to_list)}\n"
        f"Subject: {subject}\n\n"
        f"The platform ID has been logged to sends.json. Use "
        f"fetch_campaign_metrics to retrieve performance data later."
    )


@function_tool
def send_sms(
    campaign_id: str,
    variant_id: str,
    to_number: str,
    body: str,
    from_number: str,
) -> str:
    """Send an SMS via the configured SMS platform (e.g. Twilio).

    Args:
        campaign_id: The campaign this send belongs to.
        variant_id: The variant being sent (e.g. 'v1').
        to_number: Recipient phone number in E.164 format (e.g. +15551234567).
        body: Message text. 160 chars recommended for single segment.
        from_number: Sender phone number in E.164 format.
    """
    # Validate campaign
    if not _campaign_exists(campaign_id):
        return (
            f"Error: Campaign '{campaign_id}' not found. "
            "Create it with generate_copy first."
        )

    # Check adapter
    registry = get_registry()
    adapter = registry.get_sms_adapter()
    if adapter is None:
        return (
            "Error: No SMS adapter configured. "
            "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment "
            "variables to activate the Twilio integration."
        )

    # Send
    result = adapter.send_sms(
        to=to_number.strip(),
        body=body,
        from_number=from_number.strip(),
    )

    # Log the send record
    _log_send_record(campaign_id, variant_id, "sms", result)

    if not result.success:
        return (
            f"SMS send failed for variant '{variant_id}' "
            f"in campaign '{campaign_id}'.\n"
            f"Platform: {result.platform}\n"
            f"Error: {result.error}"
        )

    # Warn if the body is over the single-segment limit
    length_note = ""
    if len(body) > 160:
        length_note = (
            f"\nNote: Message is {len(body)} chars "
            f"({(len(body) - 1) // 160 + 1} SMS segments)."
        )

    return (
        f"SMS sent successfully.\n"
        f"Campaign: {campaign_id} | Variant: {variant_id}\n"
        f"Platform: {result.platform}\n"
        f"Platform ID: {result.platform_id}\n"
        f"To: {to_number}{length_note}\n\n"
        f"The platform ID has been logged to sends.json. Use "
        f"fetch_campaign_metrics to retrieve performance data later."
    )


@function_tool
def fetch_campaign_metrics(
    campaign_id: str,
    channel: str,
    start_date: str = "",
    end_date: str = "",
    site_url: str = "",
) -> str:
    """Fetch performance metrics from the external platform and auto-log
    them to the campaign's metrics.json.

    This bridges the gap between platform-specific data and the agent's
    internal metrics system. After fetching, the metrics are available
    via get_variant_metrics and analyze_campaign.

    Args:
        campaign_id: The campaign to fetch metrics for.
        channel: Which channel to fetch from -- email, sms, seo, or ads.
        start_date: Optional start date (YYYY-MM-DD). Defaults to adapter's default.
        end_date: Optional end date (YYYY-MM-DD). Defaults to today.
        site_url: Required for SEO channel -- the Search Console property URL.
    """
    # Validate campaign
    if not _campaign_exists(campaign_id):
        return (
            f"Error: Campaign '{campaign_id}' not found. "
            "Create it with generate_copy first."
        )

    channel = channel.strip().lower()
    valid_channels = {"email", "sms", "seo", "ads"}
    if channel not in valid_channels:
        return (
            f"Error: Invalid channel '{channel}'. "
            f"Must be one of: {', '.join(sorted(valid_channels))}."
        )

    registry = get_registry()
    metric_results = []

    # ---- Dispatch to the correct adapter ----

    if channel == "email":
        adapter = registry.get_email_adapter()
        if adapter is None:
            return (
                "Error: No email adapter configured. "
                "Set SENDGRID_API_KEY to activate."
            )
        # Look up platform IDs from sends.json for this campaign
        sends_path = _campaign_dir(campaign_id) / "sends.json"
        categories = [campaign_id]
        platform_id = None

        if sends_path.exists():
            sends = _read_json(sends_path)
            email_sends = [s for s in sends if s.get("channel") == "email" and s.get("success")]
            if email_sends:
                # Fetch by most recent platform_id
                platform_id = email_sends[-1].get("platform_id")

        metric_results = adapter.fetch_metrics(
            platform_id=platform_id,
            start_date=start_date or None,
            end_date=end_date or None,
            categories=categories,
        )

    elif channel == "sms":
        adapter = registry.get_sms_adapter()
        if adapter is None:
            return (
                "Error: No SMS adapter configured. "
                "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to activate."
            )
        # Look up platform IDs from sends.json
        sends_path = _campaign_dir(campaign_id) / "sends.json"
        platform_id = None

        if sends_path.exists():
            sends = _read_json(sends_path)
            sms_sends = [s for s in sends if s.get("channel") == "sms" and s.get("success")]
            if sms_sends:
                platform_id = sms_sends[-1].get("platform_id")

        metric_results = adapter.fetch_metrics(
            platform_id=platform_id,
            start_date=start_date or None,
            end_date=end_date or None,
        )

    elif channel == "seo":
        adapter = registry.get_seo_adapter()
        if adapter is None:
            return (
                "Error: No SEO adapter configured. "
                "Set GOOGLE_SERVICE_ACCOUNT_JSON to activate."
            )
        if not site_url:
            return (
                "Error: site_url is required for SEO metric fetching. "
                "Provide the Search Console property URL "
                "(e.g. 'https://example.com/')."
            )
        metric_results = adapter.fetch_metrics(
            site_url=site_url,
            start_date=start_date or None,
            end_date=end_date or None,
        )

    elif channel == "ads":
        adapter = registry.get_ads_adapter()
        if adapter is None:
            return (
                "Error: No ads adapter configured. "
                "Set GOOGLE_SERVICE_ACCOUNT_JSON and "
                "GOOGLE_ADS_CUSTOMER_ID to activate."
            )
        metric_results = adapter.fetch_metrics(
            campaign_id=campaign_id,
            start_date=start_date or None,
            end_date=end_date or None,
        )

    # ---- Auto-log fetched metrics ----

    if not metric_results:
        return (
            f"No metrics returned from {channel} platform for "
            f"campaign '{campaign_id}'. This may mean the campaign has not "
            f"accumulated data yet, or the date range is too narrow."
        )

    # Map platform_id back to variant_id using sends.json when possible
    platform_to_variant: dict[str, str] = {}
    sends_path = _campaign_dir(campaign_id) / "sends.json"
    if sends_path.exists():
        try:
            sends = _read_json(sends_path)
            for s in sends:
                pid = s.get("platform_id")
                vid = s.get("variant_id")
                if pid and vid:
                    platform_to_variant[pid] = vid
        except (json.JSONDecodeError, OSError):
            pass

    logged_count = 0
    for mr in metric_results:
        variant_id = platform_to_variant.get(mr.platform_id, mr.platform_id)
        _append_metric(
            campaign_id=campaign_id,
            variant_id=variant_id,
            metric_type=mr.metric_type,
            value=mr.value,
            metric_date=mr.date,
            notes=f"Auto-fetched from {mr.platform}",
        )
        logged_count += 1

    # ---- Format output ----

    lines = [
        f"Fetched {logged_count} metric(s) from {channel} platform "
        f"for campaign '{campaign_id}'.",
        "",
    ]

    # Group by metric type for readability
    by_type: dict[str, list] = {}
    for mr in metric_results:
        by_type.setdefault(mr.metric_type, []).append(mr)

    for mtype in sorted(by_type.keys()):
        entries = by_type[mtype]
        if len(entries) == 1:
            e = entries[0]
            lines.append(f"  {mtype}: {e.value} ({e.date})")
        else:
            lines.append(f"  {mtype}:")
            for e in sorted(entries, key=lambda x: x.date):
                lines.append(f"    {e.date}: {e.value}")

    lines.append("")
    lines.append(
        "All metrics have been auto-logged to metrics.json. "
        "Use get_variant_metrics or analyze_campaign to review."
    )

    return "\n".join(lines)


@function_tool
def check_integrations() -> str:
    """Check which external platform integrations are configured and active.

    Returns the status of each channel (email, SMS, SEO, ads) showing
    whether the required environment variables are set and whether the
    adapter loaded successfully. Use this to diagnose configuration issues
    before attempting to send or fetch metrics.
    """
    registry = get_registry()
    status = registry.get_status()

    lines = [
        "Integration Status",
        "=" * 50,
        "",
    ]

    channel_labels = {
        "email": "Email (SendGrid)",
        "sms": "SMS (Twilio)",
        "seo": "SEO (Google Search Console)",
        "ads": "Ads (Google Ads)",
    }

    active_count = 0
    for channel_key in ("email", "sms", "seo", "ads"):
        info = status[channel_key]
        label = channel_labels[channel_key]

        if info["active"]:
            indicator = "[ACTIVE]"
            active_count += 1
        elif info["configured"]:
            indicator = "[ERROR]"
        else:
            indicator = "[INACTIVE]"

        lines.append(f"  {indicator} {label}")
        lines.append(f"         {info['detail']}")
        lines.append("")

    lines.append("-" * 50)
    lines.append(f"{active_count} of 4 integrations active.")

    if active_count == 0:
        lines.append("")
        lines.append(
            "No integrations are configured. The agent can still generate "
            "and analyze copy, but cannot send it or fetch live metrics. "
            "Set the appropriate environment variables to activate integrations."
        )

    return "\n".join(lines)
