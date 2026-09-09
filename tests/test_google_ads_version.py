"""Guardrail: the Google Ads client must target a *live* API version.

Background — the 501 outage:
    The image used to pin ``google-ads==25.1.0``. That client defaults to
    Google Ads API **v18**, which Google has sunset. Once v18 was retired,
    every ``GoogleAdsService.Search`` RPC (used by the read-only
    ``account-overview`` and ``conversion-audit`` routes) failed with
    ``501 MethodNotImplemented: GRPC target method can't be resolved``.

These tests fail closed if the pin ever drifts back onto a sunset API version,
so the read-only Ads routes cannot silently break again after an image rebuild.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"

# Minimum client that targets a currently-supported (non-sunset) API version.
# google-ads 31.2.0 defaults to Google Ads API v25 (supported until ~Aug 2027).
# Anything below the v22-min client (28.1.0) can only speak a sunset version.
MIN_SUPPORTED = (31, 2, 0)

# Google Ads API versions that are sunset (or imminently sunsetting) as of this
# fix. The client's default version must never be one of these.
SUNSET_API_VERSIONS = {14, 15, 16, 17, 18, 19, 20, 21, 22}


def _pinned_google_ads_version() -> tuple[int, int, int]:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    match = re.search(r"^google-ads==(\d+)\.(\d+)\.(\d+)", text, re.MULTILINE)
    assert match, "google-ads pin not found in requirements.txt"
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def test_requirements_pin_targets_live_api_version():
    """The requirements pin must not regress to a client stuck on a sunset API."""
    pinned = _pinned_google_ads_version()
    assert pinned >= MIN_SUPPORTED, (
        f"google-ads=={'.'.join(map(str, pinned))} defaults to a sunset Google "
        f"Ads API version; pin >= {'.'.join(map(str, MIN_SUPPORTED))} which "
        "targets a live version (v25)."
    )


def test_installed_client_default_version_is_live():
    """If google-ads is installed, its default API version must not be sunset."""
    pytest.importorskip("google.ads.googleads")
    from google.ads.googleads import client as gads_client

    default_version = getattr(gads_client, "_DEFAULT_VERSION", None)
    assert default_version, "could not determine google-ads default API version"

    numeric = int(re.sub(r"\D", "", default_version))
    assert numeric not in SUNSET_API_VERSIONS, (
        f"google-ads default API version {default_version} is sunset; "
        "GoogleAdsService.Search RPCs will 501. Bump the google-ads pin."
    )
