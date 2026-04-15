"""
Twilio SMS adapter.

Implements the SmsAdapter contract using Twilio's REST API via the
``twilio`` Python SDK.  All SDK calls are wrapped in try/except so that
a Twilio outage or misconfiguration never crashes the agent.

Configuration is injected by the registry, which reads TWILIO_ACCOUNT_SID
and TWILIO_AUTH_TOKEN from the environment.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from twilio.rest import Client

from tools.integrations.base import MetricResult, SendResult, SmsAdapter

logger = logging.getLogger(__name__)


class TwilioAdapter(SmsAdapter):
    """Concrete SMS adapter backed by the Twilio Messages API.

    Args:
        account_sid: Twilio Account SID (starts with ``AC``).
        auth_token: Twilio Auth Token for the account.
    """

    # Twilio message statuses that count as a successful delivery.
    _DELIVERED_STATUSES = frozenset({"delivered", "read"})
    # Statuses that indicate a permanent failure.
    _FAILED_STATUSES = frozenset({"failed", "undelivered"})

    def __init__(self, account_sid: str, auth_token: str) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self.client = Client(account_sid, auth_token)

    # ------------------------------------------------------------------
    # SmsAdapter.send_sms
    # ------------------------------------------------------------------

    def send_sms(
        self,
        to: str,
        body: str,
        from_number: str,
    ) -> SendResult:
        """Send an SMS message via Twilio.

        Args:
            to: Recipient phone number in E.164 format.
            body: Message text.  160 characters recommended for a single
                segment, though Twilio will automatically split longer
                messages.
            from_number: Sender phone number in E.164 format (must be a
                Twilio number or verified caller ID on the account).

        Returns:
            A ``SendResult`` with the Twilio message SID on success, or
            an error description on failure.
        """
        try:
            message = self.client.messages.create(
                to=to,
                body=body,
                from_=from_number,
            )
            return SendResult(
                success=True,
                platform_id=message.sid,
                platform="twilio",
                details={
                    "status": message.status,
                    "num_segments": message.num_segments,
                },
            )
        except Exception as e:
            logger.warning("Twilio send_sms failed: %s", e)
            return SendResult(
                success=False,
                platform_id="",
                platform="twilio",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # SmsAdapter.fetch_metrics
    # ------------------------------------------------------------------

    def fetch_metrics(
        self,
        platform_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[MetricResult]:
        """Fetch SMS delivery and cost metrics from Twilio.

        Two modes of operation:

        1. **Single message** (``platform_id`` provided) -- fetches that
           message's current status and price.
        2. **Aggregate** (no ``platform_id``) -- lists messages within the
           date window and computes aggregate delivery statistics.

        Args:
            platform_id: A Twilio message SID to look up individually.
            start_date: ISO date string (YYYY-MM-DD) for query window
                start.  Defaults to 7 days ago when aggregating.
            end_date: ISO date string (YYYY-MM-DD) for query window end.
                Defaults to today when aggregating.

        Returns:
            A list of ``MetricResult`` objects.  Returns an empty list
            if the Twilio API call fails.
        """
        try:
            if platform_id:
                return self._fetch_single_message_metrics(platform_id)
            return self._fetch_aggregate_metrics(start_date, end_date)
        except Exception as e:
            logger.warning("Twilio fetch_metrics failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_single_message_metrics(
        self,
        message_sid: str,
    ) -> list[MetricResult]:
        """Return delivery and cost metrics for a single message SID."""
        message = self.client.messages(message_sid).fetch()
        today = date.today().isoformat()

        # Map delivery status to a 0.0 -- 1.0 delivery rate.
        if message.status in self._DELIVERED_STATUSES:
            delivery_value = 1.0
        elif message.status in self._FAILED_STATUSES:
            delivery_value = 0.0
        else:
            # Queued, sent, sending, etc. -- delivery not yet determined.
            delivery_value = 0.5

        results: list[MetricResult] = [
            MetricResult(
                metric_type="delivery_rate",
                value=delivery_value,
                date=today,
                platform_id=message_sid,
                platform="twilio",
                raw={
                    "status": message.status,
                    "direction": message.direction,
                    "date_sent": (
                        message.date_sent.isoformat()
                        if message.date_sent
                        else None
                    ),
                },
            ),
        ]

        # Include price as cost_per_click if available (repurposed for
        # cost-tracking; Twilio charges per segment, not per click).
        if message.price is not None:
            results.append(
                MetricResult(
                    metric_type="cost_per_click",
                    value=abs(float(message.price)),
                    date=today,
                    platform_id=message_sid,
                    platform="twilio",
                    raw={
                        "price": message.price,
                        "price_unit": message.price_unit,
                    },
                )
            )

        return results

    def _fetch_aggregate_metrics(
        self,
        start_date: str | None,
        end_date: str | None,
    ) -> list[MetricResult]:
        """Aggregate delivery stats across messages in a date window."""
        now = datetime.now(timezone.utc)

        date_sent_after: datetime = (
            datetime.fromisoformat(start_date)
            if start_date
            else now - timedelta(days=7)
        )
        date_sent_before: datetime = (
            datetime.fromisoformat(end_date)
            if end_date
            else now
        )

        # Ensure timezone-aware datetimes for the Twilio SDK.
        if date_sent_after.tzinfo is None:
            date_sent_after = date_sent_after.replace(tzinfo=timezone.utc)
        if date_sent_before.tzinfo is None:
            date_sent_before = date_sent_before.replace(tzinfo=timezone.utc)

        messages = self.client.messages.list(
            date_sent_after=date_sent_after,
            date_sent_before=date_sent_before,
        )

        total = len(messages)
        if total == 0:
            return []

        delivered = sum(
            1 for m in messages if m.status in self._DELIVERED_STATUSES
        )
        failed = sum(
            1 for m in messages if m.status in self._FAILED_STATUSES
        )
        total_cost = sum(
            abs(float(m.price)) for m in messages if m.price is not None
        )

        report_date = date.today().isoformat()
        aggregate_id = (
            f"aggregate_{date_sent_after.date().isoformat()}"
            f"_{date_sent_before.date().isoformat()}"
        )

        results: list[MetricResult] = [
            MetricResult(
                metric_type="delivery_rate",
                value=round(delivered / total, 4) if total else 0.0,
                date=report_date,
                platform_id=aggregate_id,
                platform="twilio",
                raw={
                    "total": total,
                    "delivered": delivered,
                    "failed": failed,
                    "pending": total - delivered - failed,
                },
            ),
        ]

        if total_cost > 0:
            results.append(
                MetricResult(
                    metric_type="cost_per_click",
                    value=round(total_cost / total, 6),
                    date=report_date,
                    platform_id=aggregate_id,
                    platform="twilio",
                    raw={
                        "total_cost": round(total_cost, 4),
                        "message_count": total,
                    },
                )
            )

        # NOTE: Twilio does not expose an explicit "unsubscribed" or
        # "opt-out" status on the message resource.  Opt-out tracking
        # requires monitoring inbound messages for STOP keywords or
        # using Twilio's Advanced Opt-Out management via the Messaging
        # Service.  As a result, opt_out_rate cannot be reliably
        # computed from the Messages API alone and is intentionally
        # omitted here.

        return results
