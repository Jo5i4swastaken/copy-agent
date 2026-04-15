"""
Abstract base classes defining the adapter contract for platform integrations.

Each adapter represents a single external platform (SendGrid, Twilio, Google
Search Console, Google Ads, etc.). The base classes enforce a consistent
interface so the rest of the agent does not depend on any specific SDK.

Two data classes standardize what comes back from every adapter:
    SendResult  -- outcome of sending copy to a platform
    MetricResult -- a single metric data point fetched from a platform

New platforms are added by subclassing the appropriate adapter and
implementing its abstract methods. The registry (registry.py) handles
discovery and instantiation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class SendResult:
    """Result of sending copy via a platform.

    Attributes:
        success: Whether the send completed without error.
        platform_id: The platform's own identifier for this send
            (e.g. SendGrid message ID, Twilio SID).
        platform: Short platform name (e.g. "sendgrid", "twilio").
        details: Platform-specific response data for debugging or auditing.
        error: Human-readable error message when success is False.
    """

    success: bool
    platform_id: str
    platform: str
    details: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class MetricResult:
    """A single metric data point fetched from a platform.

    Attributes:
        metric_type: Must match one of the VALID_METRIC_TYPES defined
            in metrics_tools.py (e.g. "open_rate", "click_rate").
        value: Numeric metric value.
        date: ISO-format date string (YYYY-MM-DD) the metric applies to.
        platform_id: What was measured -- message ID, campaign ID, URL, etc.
        platform: Short platform name (e.g. "sendgrid", "google_search_console").
        raw: Full platform response preserved for debugging.
    """

    metric_type: str
    value: float
    date: str
    platform_id: str
    platform: str
    raw: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Adapter contracts
# ---------------------------------------------------------------------------

class EmailAdapter(ABC):
    """Contract for email platform integrations (e.g. SendGrid, Mailgun).

    Implementers must provide both send and metric-fetch capabilities so the
    agent can close the generate-send-measure loop.
    """

    @abstractmethod
    def send_email(
        self,
        to: list[str],
        subject: str,
        html_content: str,
        from_email: str,
        reply_to: str | None = None,
        categories: list[str] | None = None,
    ) -> SendResult:
        """Send an email through the platform.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            html_content: HTML body of the email.
            from_email: Sender email address.
            reply_to: Optional reply-to address.
            categories: Optional tags/categories for tracking and filtering.

        Returns:
            A SendResult capturing the platform's response.
        """
        ...

    @abstractmethod
    def fetch_metrics(
        self,
        platform_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        categories: list[str] | None = None,
    ) -> list[MetricResult]:
        """Fetch email performance metrics from the platform.

        Implementers should map platform-specific metric names to the
        canonical types in VALID_METRIC_TYPES (open_rate, click_rate, etc.).

        Args:
            platform_id: Filter to a specific message or campaign ID.
            start_date: ISO date string for the start of the query window.
            end_date: ISO date string for the end of the query window.
            categories: Filter by previously-assigned categories.

        Returns:
            A list of MetricResult objects, one per metric/date combination.
        """
        ...


class SmsAdapter(ABC):
    """Contract for SMS platform integrations (e.g. Twilio, Vonage).

    Provides send and metric-fetch for text message campaigns.
    """

    @abstractmethod
    def send_sms(
        self,
        to: str,
        body: str,
        from_number: str,
    ) -> SendResult:
        """Send an SMS message through the platform.

        Args:
            to: Recipient phone number in E.164 format.
            body: Message text (160 chars recommended for single segment).
            from_number: Sender phone number in E.164 format.

        Returns:
            A SendResult capturing the platform's response.
        """
        ...

    @abstractmethod
    def fetch_metrics(
        self,
        platform_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[MetricResult]:
        """Fetch SMS delivery and engagement metrics.

        Args:
            platform_id: Filter to a specific message SID.
            start_date: ISO date string for query window start.
            end_date: ISO date string for query window end.

        Returns:
            A list of MetricResult objects (delivery_rate, opt_out_rate, etc.).
        """
        ...


class SeoAdapter(ABC):
    """Contract for SEO analytics integrations (e.g. Google Search Console).

    Read-only -- there is no "send" action. The adapter fetches search
    performance data that the agent uses to evaluate SEO copy variants.
    """

    @abstractmethod
    def fetch_metrics(
        self,
        site_url: str,
        start_date: str | None = None,
        end_date: str | None = None,
        query: str | None = None,
        page: str | None = None,
        limit: int = 20,
    ) -> list[MetricResult]:
        """Fetch search performance metrics for a site.

        Args:
            site_url: The property URL in Search Console
                (e.g. "https://example.com/").
            start_date: ISO date string for query window start.
            end_date: ISO date string for query window end.
            query: Filter to rows matching this search query.
            page: Filter to rows matching this page URL.
            limit: Maximum number of rows to return.

        Returns:
            A list of MetricResult objects (impressions, clicks, ctr,
            search_position).
        """
        ...


class AdsAdapter(ABC):
    """Contract for advertising platform integrations (e.g. Google Ads).

    Read-only for metrics. Ad creation workflows are intentionally excluded
    from this first iteration -- the agent generates copy, and a human
    uploads it to the ad platform.
    """

    @abstractmethod
    def fetch_metrics(
        self,
        campaign_id: str | None = None,
        ad_group_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[MetricResult]:
        """Fetch ad performance metrics from the platform.

        Args:
            campaign_id: Filter to a specific ad campaign.
            ad_group_id: Filter to a specific ad group within a campaign.
            start_date: ISO date string for query window start.
            end_date: ISO date string for query window end.

        Returns:
            A list of MetricResult objects (impressions, clicks, ctr,
            cost_per_click, roas, conversion_rate).
        """
        ...
