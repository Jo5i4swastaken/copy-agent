"""
SendGrid email adapter.

Implements the EmailAdapter contract using SendGrid's v3 API via the
official ``sendgrid`` Python SDK. The registry instantiates this class
when the ``SENDGRID_API_KEY`` environment variable is present.

Capabilities:
    - Send transactional/marketing emails through the Mail Send v3 endpoint.
    - Fetch aggregate email performance metrics (open rate, click rate,
      unsubscribe rate) from the Stats v3 endpoint.

Limitations:
    - SendGrid's Stats API returns aggregate data per day, not per-message.
      The ``platform_id`` parameter on ``fetch_metrics`` is accepted for
      interface compliance but cannot filter to a single message. A log
      warning is emitted when it is provided.
    - Rate metrics (open_rate, click_rate, unsubscribe_rate) are computed
      from the raw counters returned by SendGrid. If the denominator
      (requests or delivered) is zero for a given day, the rate is reported
      as 0.0 rather than omitted.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import sendgrid
from sendgrid.helpers.mail import Category, Mail, ReplyTo

from tools.integrations.base import EmailAdapter, MetricResult, SendResult

logger = logging.getLogger(__name__)


class SendGridAdapter(EmailAdapter):
    """Concrete email adapter backed by the SendGrid v3 API.

    Args:
        api_key: A valid SendGrid API key with Mail Send and Stats
            permissions.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self.client = sendgrid.SendGridAPIClient(api_key=api_key)

    # ------------------------------------------------------------------
    # EmailAdapter.send_email
    # ------------------------------------------------------------------

    def send_email(
        self,
        to: list[str],
        subject: str,
        html_content: str,
        from_email: str,
        reply_to: str | None = None,
        categories: list[str] | None = None,
    ) -> SendResult:
        """Send an email through SendGrid's Mail Send v3 endpoint.

        Builds a ``Mail`` object from the provided parameters, attaches
        optional reply-to and category metadata, and dispatches through
        the SDK client.

        Returns:
            A ``SendResult`` with the SendGrid ``X-Message-Id`` header as
            the ``platform_id`` on success, or an error description on
            failure.
        """
        try:
            message = Mail(
                from_email=from_email,
                to_emails=to,
                subject=subject,
                html_content=html_content,
            )

            if reply_to is not None:
                message.reply_to = ReplyTo(reply_to)

            if categories:
                for cat in categories:
                    message.category = Category(cat)

            response = self.client.send(message)

            platform_id = ""
            if response.headers:
                platform_id = response.headers.get("X-Message-Id", "")

            return SendResult(
                success=True,
                platform_id=platform_id,
                platform="sendgrid",
                details={"status_code": response.status_code},
            )

        except Exception as e:
            logger.warning("SendGrid send_email failed: %s", e)
            return SendResult(
                success=False,
                platform_id="",
                platform="sendgrid",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # EmailAdapter.fetch_metrics
    # ------------------------------------------------------------------

    def fetch_metrics(
        self,
        platform_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        categories: list[str] | None = None,
    ) -> list[MetricResult]:
        """Fetch email performance metrics from the SendGrid Stats API.

        Uses ``GET /v3/stats`` for global statistics, or
        ``GET /v3/categories/stats`` when *categories* are provided.

        The raw SendGrid counters are converted into canonical rate
        metrics:

        * **open_rate** -- ``unique_opens / requests`` (when requests > 0)
        * **click_rate** -- ``unique_clicks / delivered`` (when delivered > 0)
        * **unsubscribe_rate** -- ``unsubscribes / delivered`` (when delivered > 0)

        Args:
            platform_id: Accepted for interface compliance. SendGrid stats
                are aggregate, so per-message filtering is not possible.
                A warning is logged if this parameter is provided.
            start_date: ISO date string (YYYY-MM-DD) for the start of the
                query window. Defaults to 7 days ago.
            end_date: ISO date string (YYYY-MM-DD) for the end of the
                query window. Defaults to today.
            categories: Optional list of SendGrid categories to filter by.
                When provided, the categories stats endpoint is used.

        Returns:
            A list of ``MetricResult`` objects, one per metric per day.
            Returns an empty list on error.
        """
        if platform_id:
            logger.warning(
                "SendGrid Stats API is aggregate -- platform_id '%s' "
                "cannot be used to filter to a single message. "
                "Returning global/category stats instead.",
                platform_id,
            )

        today = datetime.now(timezone.utc).date()
        resolved_start = start_date or (today - timedelta(days=7)).isoformat()
        resolved_end = end_date or today.isoformat()

        params: dict[str, Any] = {
            "start_date": resolved_start,
            "end_date": resolved_end,
        }

        try:
            if categories:
                # /v3/categories/stats requires the categories query param
                params["categories"] = "&categories=".join(categories)
                response = self.client.client.categories.stats.get(
                    query_params=params,
                )
            else:
                response = self.client.client.stats.get(
                    query_params=params,
                )

            body = response.to_dict
            # sendgrid-python returns the body as a property; when the
            # SDK version exposes it as a callable, handle both.
            if callable(body):
                body = body()

            return self._parse_stats_response(
                body,
                identifier=platform_id or "aggregate",
            )

        except Exception as e:
            logger.warning("SendGrid fetch_metrics failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_stats_response(
        data: list[dict[str, Any]],
        identifier: str,
    ) -> list[MetricResult]:
        """Convert the SendGrid stats JSON into canonical MetricResult objects.

        SendGrid returns a list of date objects, each containing a list of
        ``stats`` entries. Each stats entry has a ``metrics`` dict with
        raw counters (requests, delivered, opens, unique_opens, clicks,
        unique_clicks, unsubscribes, etc.).

        This method computes the three canonical rates and emits one
        ``MetricResult`` per rate per date.

        Args:
            data: Parsed JSON body from the SendGrid stats endpoint.
            identifier: Value to use for the ``platform_id`` field
                (typically "aggregate" or the campaign/category name).

        Returns:
            A flat list of ``MetricResult`` instances.
        """
        results: list[MetricResult] = []

        if not isinstance(data, list):
            logger.warning(
                "Unexpected SendGrid stats response format: expected list, "
                "got %s",
                type(data).__name__,
            )
            return results

        for day_entry in data:
            date_str = day_entry.get("date", "")
            stats_list = day_entry.get("stats", [])

            for stat_block in stats_list:
                metrics: dict[str, int] = stat_block.get("metrics", {})

                requests = metrics.get("requests", 0)
                delivered = metrics.get("delivered", 0)
                unique_opens = metrics.get("unique_opens", 0)
                unique_clicks = metrics.get("unique_clicks", 0)
                unsubscribes = metrics.get("unsubscribes", 0)

                # open_rate = unique_opens / requests
                open_rate = (
                    unique_opens / requests if requests > 0 else 0.0
                )
                results.append(
                    MetricResult(
                        metric_type="open_rate",
                        value=round(open_rate, 6),
                        date=date_str,
                        platform_id=identifier,
                        platform="sendgrid",
                        raw=metrics,
                    )
                )

                # click_rate = unique_clicks / delivered
                click_rate = (
                    unique_clicks / delivered if delivered > 0 else 0.0
                )
                results.append(
                    MetricResult(
                        metric_type="click_rate",
                        value=round(click_rate, 6),
                        date=date_str,
                        platform_id=identifier,
                        platform="sendgrid",
                        raw=metrics,
                    )
                )

                # unsubscribe_rate = unsubscribes / delivered
                unsub_rate = (
                    unsubscribes / delivered if delivered > 0 else 0.0
                )
                results.append(
                    MetricResult(
                        metric_type="unsubscribe_rate",
                        value=round(unsub_rate, 6),
                        date=date_str,
                        platform_id=identifier,
                        platform="sendgrid",
                        raw=metrics,
                    )
                )

        return results
