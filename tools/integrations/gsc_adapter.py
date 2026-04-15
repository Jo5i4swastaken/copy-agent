"""
Google Search Console adapter for fetching SEO performance metrics.

Implements the SeoAdapter contract using the Google Search Console
searchAnalytics.query API. Authenticates via a Google service-account
JSON key file and returns normalised MetricResult objects for clicks,
impressions, CTR, and average search position.

Requires:
    pip install google-api-python-client google-auth
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from tools.integrations.base import MetricResult, SeoAdapter

logger = logging.getLogger(__name__)

# Google Search Console data typically lags by ~3 days.
_GSC_DATA_DELAY_DAYS = 3
_DEFAULT_LOOKBACK_DAYS = 28

_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


class GoogleSearchConsoleAdapter(SeoAdapter):
    """Concrete SeoAdapter backed by the Google Search Console API.

    Args:
        service_account_json: Filesystem path to a Google Cloud
            service-account key file (JSON) that has been granted
            read access to the target Search Console properties.
    """

    def __init__(self, service_account_json: str) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json,
            scopes=_SCOPES,
        )
        self.service = build("searchconsole", "v1", credentials=credentials)

    # ------------------------------------------------------------------
    # SeoAdapter contract
    # ------------------------------------------------------------------

    def fetch_metrics(
        self,
        site_url: str,
        start_date: str | None = None,
        end_date: str | None = None,
        query: str | None = None,
        page: str | None = None,
        limit: int = 20,
    ) -> list[MetricResult]:
        """Fetch search performance metrics from Google Search Console.

        Returns up to ``limit`` rows of daily data, each row expanded
        into four MetricResult objects (clicks, impressions, ctr,
        search_position).

        Args:
            site_url: The Search Console property URL
                (e.g. ``"https://example.com/"``).
            start_date: ISO date (YYYY-MM-DD) for the query window start.
                Defaults to 28 days ago.
            end_date: ISO date (YYYY-MM-DD) for the query window end.
                Defaults to 3 days ago (accounts for GSC data delay).
            query: Optional search-query substring filter.
            page: Optional page-URL substring filter.
            limit: Maximum number of rows to return from the API.

        Returns:
            A list of MetricResult objects, or an empty list on error.
        """
        today = date.today()

        resolved_start = start_date or (
            today - timedelta(days=_DEFAULT_LOOKBACK_DAYS)
        ).isoformat()
        resolved_end = end_date or (
            today - timedelta(days=_GSC_DATA_DELAY_DAYS)
        ).isoformat()

        body: dict[str, Any] = {
            "startDate": resolved_start,
            "endDate": resolved_end,
            "dimensions": ["date"],
            "rowLimit": limit,
        }

        # Build dimension filters when query or page filters are provided.
        filters: list[dict[str, str]] = []
        if query:
            filters.append(
                {
                    "dimension": "query",
                    "operator": "contains",
                    "expression": query,
                }
            )
        if page:
            filters.append(
                {
                    "dimension": "page",
                    "operator": "contains",
                    "expression": page,
                }
            )
        if filters:
            body["dimensionFilterGroups"] = [
                {"groupType": "and", "filters": filters}
            ]

        try:
            response: dict[str, Any] = (
                self.service.searchanalytics()
                .query(siteUrl=site_url, body=body)
                .execute()
            )
        except HttpError as exc:
            logger.error(
                "Google Search Console API HTTP error for %s: %s",
                site_url,
                exc,
            )
            return []
        except Exception:
            logger.exception(
                "Unexpected error fetching Search Console data for %s",
                site_url,
            )
            return []

        rows: list[dict[str, Any]] = response.get("rows", [])
        if not rows:
            logger.info(
                "No Search Console data returned for %s (%s to %s).",
                site_url,
                resolved_start,
                resolved_end,
            )
            return []

        platform_id = page if page else site_url

        results: list[MetricResult] = []
        for row in rows:
            row_date = row["keys"][0]
            raw = dict(row)

            results.append(
                MetricResult(
                    metric_type="clicks",
                    value=float(row["clicks"]),
                    date=row_date,
                    platform_id=platform_id,
                    platform="google_search_console",
                    raw=raw,
                )
            )
            results.append(
                MetricResult(
                    metric_type="impressions",
                    value=float(row["impressions"]),
                    date=row_date,
                    platform_id=platform_id,
                    platform="google_search_console",
                    raw=raw,
                )
            )
            results.append(
                MetricResult(
                    metric_type="ctr",
                    value=float(row["ctr"]),
                    date=row_date,
                    platform_id=platform_id,
                    platform="google_search_console",
                    raw=raw,
                )
            )
            results.append(
                MetricResult(
                    metric_type="search_position",
                    value=float(row["position"]),
                    date=row_date,
                    platform_id=platform_id,
                    platform="google_search_console",
                    raw=raw,
                )
            )

        logger.debug(
            "Fetched %d metric results (%d rows) from Search Console for %s.",
            len(results),
            len(rows),
            site_url,
        )
        return results
