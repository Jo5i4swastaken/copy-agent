"""
Google Ads adapter for fetching ad campaign performance metrics.

Implements the AdsAdapter contract using the Google Ads API via the
``google-ads`` Python SDK. Authenticates with a Google service-account
key file and a developer token. Returns normalised MetricResult objects
for impressions, clicks, CTR, CPC, conversion rate, and ROAS.

Read-only — the agent generates ad copy for humans to upload. This
adapter only fetches performance data.

Requires:
    pip install google-ads google-auth
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.oauth2 import service_account

from tools.integrations.base import AdsAdapter, MetricResult

logger = logging.getLogger(__name__)

_DEFAULT_LOOKBACK_DAYS = 30
# Google Ads data is usually available with a ~1 day delay.
_ADS_DATA_DELAY_DAYS = 1

_SCOPES = ["https://www.googleapis.com/auth/adwords"]

_CAMPAIGN_QUERY = """
    SELECT
        campaign.id,
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.ctr,
        metrics.average_cpc,
        metrics.conversions,
        metrics.cost_micros,
        metrics.all_conversions_value,
        segments.date
    FROM campaign
    WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
"""

_AD_GROUP_QUERY = """
    SELECT
        ad_group.id,
        ad_group.name,
        campaign.id,
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.ctr,
        metrics.average_cpc,
        metrics.conversions,
        metrics.cost_micros,
        metrics.all_conversions_value,
        segments.date
    FROM ad_group
    WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
"""


class GoogleAdsAdapter(AdsAdapter):
    """Concrete AdsAdapter backed by the Google Ads API.

    Args:
        service_account_json: Filesystem path to a Google Cloud
            service-account key file (JSON) with domain-wide delegation
            configured for the Google Ads account.
        customer_id: Google Ads customer ID (digits only, no dashes).
    """

    def __init__(self, service_account_json: str, customer_id: str) -> None:
        self._customer_id = customer_id.replace("-", "")

        developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        if not developer_token:
            logger.warning(
                "GOOGLE_ADS_DEVELOPER_TOKEN not set. API calls will likely "
                "fail with an authentication error."
            )

        credentials = service_account.Credentials.from_service_account_file(
            service_account_json,
            scopes=_SCOPES,
        )

        self.client = GoogleAdsClient(
            credentials=credentials,
            developer_token=developer_token,
        )

    # ------------------------------------------------------------------
    # AdsAdapter contract
    # ------------------------------------------------------------------

    def fetch_metrics(
        self,
        campaign_id: str | None = None,
        ad_group_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[MetricResult]:
        """Fetch ad performance metrics from Google Ads.

        Uses Google Ads Query Language (GAQL) to pull campaign- or
        ad-group-level performance data. Each row is expanded into up
        to 6 MetricResult objects: impressions, clicks, ctr,
        cost_per_click, conversion_rate, and roas.

        Args:
            campaign_id: Optional Google Ads campaign ID to filter to.
            ad_group_id: Optional ad group ID (queries the ad_group
                table instead of campaign when provided).
            start_date: ISO date (YYYY-MM-DD) for the query window start.
                Defaults to 30 days ago.
            end_date: ISO date (YYYY-MM-DD) for the query window end.
                Defaults to yesterday.

        Returns:
            A list of MetricResult objects, or an empty list on error.
        """
        today = date.today()
        resolved_start = start_date or (
            today - timedelta(days=_DEFAULT_LOOKBACK_DAYS)
        ).isoformat()
        resolved_end = end_date or (
            today - timedelta(days=_ADS_DATA_DELAY_DAYS)
        ).isoformat()

        if ad_group_id:
            query = _AD_GROUP_QUERY.format(
                start_date=resolved_start,
                end_date=resolved_end,
            )
            query += f"    AND ad_group.id = {ad_group_id}"
        else:
            query = _CAMPAIGN_QUERY.format(
                start_date=resolved_start,
                end_date=resolved_end,
            )
            if campaign_id:
                query += f"    AND campaign.id = {campaign_id}"

        try:
            ga_service = self.client.get_service("GoogleAdsService")
            response = ga_service.search_stream(
                customer_id=self._customer_id,
                query=query,
            )
            return self._parse_response(response, ad_group_id is not None)

        except GoogleAdsException as exc:
            for error in exc.failure.errors:
                logger.error(
                    "Google Ads API error: [%s] %s",
                    error.error_code,
                    error.message,
                )
            return []
        except Exception:
            logger.exception("Unexpected error fetching Google Ads data.")
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(
        stream_response: Any,
        is_ad_group: bool,
    ) -> list[MetricResult]:
        """Convert the GAQL stream response into canonical MetricResult objects.

        Each row yields up to 6 metrics: impressions, clicks, ctr,
        cost_per_click, conversion_rate, roas.
        """
        results: list[MetricResult] = []

        for batch in stream_response:
            for row in batch.results:
                metrics = row.metrics
                segment_date = row.segments.date  # YYYY-MM-DD string

                if is_ad_group:
                    pid = str(row.ad_group.id)
                    entity_name = row.ad_group.name
                else:
                    pid = str(row.campaign.id)
                    entity_name = row.campaign.name

                raw: dict[str, Any] = {
                    "entity_name": entity_name,
                    "impressions": metrics.impressions,
                    "clicks": metrics.clicks,
                    "cost_micros": metrics.cost_micros,
                    "conversions": metrics.conversions,
                }

                # -- impressions --
                results.append(
                    MetricResult(
                        metric_type="impressions",
                        value=float(metrics.impressions),
                        date=segment_date,
                        platform_id=pid,
                        platform="google_ads",
                        raw=raw,
                    )
                )

                # -- clicks --
                results.append(
                    MetricResult(
                        metric_type="clicks",
                        value=float(metrics.clicks),
                        date=segment_date,
                        platform_id=pid,
                        platform="google_ads",
                        raw=raw,
                    )
                )

                # -- ctr (Google Ads returns as a fraction, e.g. 0.05) --
                results.append(
                    MetricResult(
                        metric_type="ctr",
                        value=float(metrics.ctr),
                        date=segment_date,
                        platform_id=pid,
                        platform="google_ads",
                        raw=raw,
                    )
                )

                # -- cost_per_click (micros -> dollars) --
                cpc = (
                    metrics.average_cpc / 1_000_000
                    if metrics.average_cpc
                    else 0.0
                )
                results.append(
                    MetricResult(
                        metric_type="cost_per_click",
                        value=round(cpc, 4),
                        date=segment_date,
                        platform_id=pid,
                        platform="google_ads",
                        raw=raw,
                    )
                )

                # -- conversion_rate (conversions / clicks) --
                conv_rate = (
                    metrics.conversions / metrics.clicks
                    if metrics.clicks > 0
                    else 0.0
                )
                results.append(
                    MetricResult(
                        metric_type="conversion_rate",
                        value=round(conv_rate, 6),
                        date=segment_date,
                        platform_id=pid,
                        platform="google_ads",
                        raw=raw,
                    )
                )

                # -- roas (conversion value / cost) --
                cost_dollars = metrics.cost_micros / 1_000_000
                roas = (
                    metrics.all_conversions_value / cost_dollars
                    if cost_dollars > 0
                    else 0.0
                )
                results.append(
                    MetricResult(
                        metric_type="roas",
                        value=round(roas, 4),
                        date=segment_date,
                        platform_id=pid,
                        platform="google_ads",
                        raw=raw,
                    )
                )

        logger.debug("Parsed %d metric results from Google Ads.", len(results))
        return results
