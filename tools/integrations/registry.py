"""
Registry for platform adapters.

Adapters are registered by channel (email, sms, seo, ads) and loaded
based on environment variables. This allows the agent to work with
whichever platforms the user has configured.

Usage:
    registry = get_registry()                 # singleton access
    email = registry.get_email_adapter()      # Returns SendGridAdapter if SENDGRID_API_KEY is set
    status = registry.get_status()            # Dict showing which integrations are active

Configuration via environment variables:
    SENDGRID_API_KEY              -> activates SendGrid email adapter
    TWILIO_ACCOUNT_SID            -> activates Twilio SMS adapter
    TWILIO_AUTH_TOKEN              -> (required with SID)
    GOOGLE_SERVICE_ACCOUNT_JSON   -> activates Google Search Console + Google Ads adapters
    GOOGLE_ADS_CUSTOMER_ID        -> (required for Google Ads)

Design notes:
    - Singleton: one registry instance is shared across all tools via get_registry().
    - Lazy loading: adapter classes and their SDKs are imported only when
      first requested, so missing SDK packages do not break the agent.
    - Fail-safe: if an adapter cannot be instantiated (missing SDK, bad
      credentials), the registry logs the error and returns None rather
      than crashing the agent.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from tools.integrations.base import (
    AdsAdapter,
    EmailAdapter,
    SeoAdapter,
    SmsAdapter,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

class AdapterRegistry:
    """Central registry that discovers and caches platform adapters.

    Each adapter is instantiated at most once (lazy singleton per channel).
    Detection is based on environment variables so the user controls which
    integrations are active by setting or unsetting keys.
    """

    def __init__(self) -> None:
        self._email: Optional[EmailAdapter] = None
        self._sms: Optional[SmsAdapter] = None
        self._seo: Optional[SeoAdapter] = None
        self._ads: Optional[AdsAdapter] = None

        # Track whether we have already attempted to load each adapter
        # so we do not retry on every call after a failed load.
        self._email_attempted: bool = False
        self._sms_attempted: bool = False
        self._seo_attempted: bool = False
        self._ads_attempted: bool = False

    # -- Email (SendGrid) --------------------------------------------------

    def get_email_adapter(self) -> Optional[EmailAdapter]:
        """Return the active email adapter, or None if not configured.

        Currently supports SendGrid. To add a second email provider, add
        another elif branch here and a new adapter class.
        """
        if self._email is not None:
            return self._email
        if self._email_attempted:
            return None
        self._email_attempted = True

        api_key = os.environ.get("SENDGRID_API_KEY")
        if not api_key:
            logger.debug("SENDGRID_API_KEY not set -- email adapter inactive.")
            return None

        try:
            from tools.integrations.sendgrid_adapter import SendGridAdapter
            self._email = SendGridAdapter(api_key=api_key)
            logger.info("SendGrid email adapter loaded.")
        except ImportError:
            logger.warning(
                "sendgrid package not installed. "
                "Run: pip install sendgrid"
            )
        except Exception as exc:
            logger.error("Failed to initialize SendGrid adapter: %s", exc)

        return self._email

    # -- SMS (Twilio) ------------------------------------------------------

    def get_sms_adapter(self) -> Optional[SmsAdapter]:
        """Return the active SMS adapter, or None if not configured.

        Currently supports Twilio. Requires both TWILIO_ACCOUNT_SID and
        TWILIO_AUTH_TOKEN to be set.
        """
        if self._sms is not None:
            return self._sms
        if self._sms_attempted:
            return None
        self._sms_attempted = True

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        if not account_sid or not auth_token:
            logger.debug("Twilio credentials not set -- SMS adapter inactive.")
            return None

        try:
            from tools.integrations.twilio_adapter import TwilioAdapter
            self._sms = TwilioAdapter(
                account_sid=account_sid,
                auth_token=auth_token,
            )
            logger.info("Twilio SMS adapter loaded.")
        except ImportError:
            logger.warning(
                "twilio package not installed. "
                "Run: pip install twilio"
            )
        except Exception as exc:
            logger.error("Failed to initialize Twilio adapter: %s", exc)

        return self._sms

    # -- SEO (Google Search Console) ---------------------------------------

    def get_seo_adapter(self) -> Optional[SeoAdapter]:
        """Return the active SEO adapter, or None if not configured.

        Requires GOOGLE_SERVICE_ACCOUNT_JSON pointing to a service-account
        key file with Search Console API access.
        """
        if self._seo is not None:
            return self._seo
        if self._seo_attempted:
            return None
        self._seo_attempted = True

        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not sa_json:
            logger.debug(
                "GOOGLE_SERVICE_ACCOUNT_JSON not set -- SEO adapter inactive."
            )
            return None

        try:
            from tools.integrations.gsc_adapter import GoogleSearchConsoleAdapter
            self._seo = GoogleSearchConsoleAdapter(
                service_account_json=sa_json,
            )
            logger.info("Google Search Console adapter loaded.")
        except ImportError:
            logger.warning(
                "google-api-python-client or google-auth not installed. "
                "Run: pip install google-api-python-client google-auth"
            )
        except Exception as exc:
            logger.error(
                "Failed to initialize Google Search Console adapter: %s", exc
            )

        return self._seo

    # -- Ads (Google Ads) --------------------------------------------------

    def get_ads_adapter(self) -> Optional[AdsAdapter]:
        """Return the active ads adapter, or None if not configured.

        Requires both GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_ADS_CUSTOMER_ID.
        """
        if self._ads is not None:
            return self._ads
        if self._ads_attempted:
            return None
        self._ads_attempted = True

        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
        if not sa_json or not customer_id:
            logger.debug(
                "Google Ads credentials not set -- ads adapter inactive."
            )
            return None

        try:
            from tools.integrations.google_ads_adapter import GoogleAdsAdapter
            self._ads = GoogleAdsAdapter(
                service_account_json=sa_json,
                customer_id=customer_id,
            )
            logger.info("Google Ads adapter loaded.")
        except ImportError:
            logger.warning(
                "google-ads package not installed. "
                "Run: pip install google-ads"
            )
        except Exception as exc:
            logger.error("Failed to initialize Google Ads adapter: %s", exc)

        return self._ads

    # -- Status ------------------------------------------------------------

    def get_status(self) -> dict[str, dict[str, str]]:
        """Return a summary of which integrations are configured and active.

        Each channel maps to a dict with:
            configured: bool  -- are the required env vars present?
            active: bool      -- did the adapter load successfully?
            platform: str     -- which platform is providing this channel
            detail: str       -- human-readable explanation

        This is designed to be both machine-readable (for tool logic) and
        human-readable (for the check_integrations tool output).
        """
        status: dict[str, dict[str, str]] = {}

        # Email / SendGrid
        sg_key = os.environ.get("SENDGRID_API_KEY")
        email_adapter = self.get_email_adapter()
        status["email"] = {
            "configured": bool(sg_key),
            "active": email_adapter is not None,
            "platform": "sendgrid" if sg_key else "none",
            "detail": (
                "SendGrid active"
                if email_adapter
                else (
                    "SENDGRID_API_KEY set but adapter failed to load"
                    if sg_key
                    else "Set SENDGRID_API_KEY to activate"
                )
            ),
        }

        # SMS / Twilio
        tw_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        tw_token = os.environ.get("TWILIO_AUTH_TOKEN")
        sms_adapter = self.get_sms_adapter()
        status["sms"] = {
            "configured": bool(tw_sid and tw_token),
            "active": sms_adapter is not None,
            "platform": "twilio" if (tw_sid and tw_token) else "none",
            "detail": (
                "Twilio active"
                if sms_adapter
                else (
                    "Twilio credentials set but adapter failed to load"
                    if (tw_sid and tw_token)
                    else "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to activate"
                )
            ),
        }

        # SEO / Google Search Console
        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        seo_adapter = self.get_seo_adapter()
        status["seo"] = {
            "configured": bool(sa_json),
            "active": seo_adapter is not None,
            "platform": "google_search_console" if sa_json else "none",
            "detail": (
                "Google Search Console active"
                if seo_adapter
                else (
                    "GOOGLE_SERVICE_ACCOUNT_JSON set but adapter failed to load"
                    if sa_json
                    else "Set GOOGLE_SERVICE_ACCOUNT_JSON to activate"
                )
            ),
        }

        # Ads / Google Ads
        ads_customer = os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
        ads_adapter = self.get_ads_adapter()
        status["ads"] = {
            "configured": bool(sa_json and ads_customer),
            "active": ads_adapter is not None,
            "platform": "google_ads" if (sa_json and ads_customer) else "none",
            "detail": (
                "Google Ads active"
                if ads_adapter
                else (
                    "Google Ads credentials set but adapter failed to load"
                    if (sa_json and ads_customer)
                    else "Set GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_ADS_CUSTOMER_ID to activate"
                )
            ),
        }

        return status

    def reset(self) -> None:
        """Clear all cached adapters so they will be re-detected on next access.

        Useful for testing or after environment variable changes at runtime.
        """
        self._email = None
        self._sms = None
        self._seo = None
        self._ads = None
        self._email_attempted = False
        self._sms_attempted = False
        self._seo_attempted = False
        self._ads_attempted = False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: Optional[AdapterRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> AdapterRegistry:
    """Return the shared AdapterRegistry singleton.

    Thread-safe. The registry is created on first call and reused thereafter.
    """
    global _registry
    if _registry is None:
        with _registry_lock:
            # Double-checked locking
            if _registry is None:
                _registry = AdapterRegistry()
    return _registry
