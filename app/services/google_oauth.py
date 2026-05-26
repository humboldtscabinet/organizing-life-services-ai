"""Centralized OAuth client builder for Google Marketing Platform APIs.

All Google APIs that require user-OAuth (rather than service-account)
share the same flow: a developer-issued client_id + client_secret pair,
plus a long-lived refresh_token generated once via the consent flow.

Service-account auth (GA4, GSC, Sheets) is NOT handled here — those
services already use ``GOOGLE_APPLICATION_CREDENTIALS`` directly.

Currently powers:
    - Google Ads        (Phase A)
    - Google Business   (Phase B, planned)
    - Tag Manager       (Phase C, planned)
"""
from __future__ import annotations

import os
from typing import Optional


def _env(key: str) -> Optional[str]:
    val = os.getenv(key)
    return val.strip() if val else None


def google_ads_client():
    """Return an authenticated ``GoogleAdsClient`` or ``None`` if unconfigured.

    Returns ``None`` (rather than raising) so callers can fall back to the
    GA4-derived Ads data path when the developer token has not yet been
    provisioned.
    """
    developer_token = _env("GOOGLE_ADS_DEVELOPER_TOKEN")
    client_id = _env("GOOGLE_ADS_CLIENT_ID")
    client_secret = _env("GOOGLE_ADS_CLIENT_SECRET")
    refresh_token = _env("GOOGLE_ADS_REFRESH_TOKEN")

    if not all([developer_token, client_id, client_secret, refresh_token]):
        return None

    # Imported lazily so the rest of the app can boot without google-ads
    # installed (useful for slim test environments).
    from google.ads.googleads.client import GoogleAdsClient  # type: ignore

    config = {
        "developer_token": developer_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    login_customer_id = _env("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if login_customer_id:
        config["login_customer_id"] = login_customer_id.replace("-", "")

    return GoogleAdsClient.load_from_dict(config)
