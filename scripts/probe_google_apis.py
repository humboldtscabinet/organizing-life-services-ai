#!/usr/bin/env python3
"""Probe OLS Google APIs with the service account. Never prints secrets.

Checks: GA4 Admin, GA4 Data, Search Console, GTM, Sheets, GBP.
Does not call the Google Ads API (that is user OAuth, not the SA).

Usage (Mac mini, no image rebuild needed if the host has this file):

  cd /Users/aiagentecosystem/services/ols
  docker exec -i --env-file .env ols-api python3 - < scripts/probe_google_apis.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDS_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/app/credentials/google-service-account.json",
)


def classify(exc: Exception) -> str:
    text = str(exc)
    lower = text.lower()
    if "SERVICE_DISABLED" in text or "has not been used" in text or "it is disabled" in lower:
        return "SERVICE_DISABLED"
    if "429" in text or "quota" in lower or "rate" in lower:
        return "429"
    if "403" in text or "permission" in lower or "insufficient" in lower:
        return "403"
    if "404" in text or "not found" in lower:
        return "404"
    return "ERROR"


def creds(scopes: list[str]):
    return service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)


def check_ga4_admin() -> dict:
    prop = os.getenv("GA4_PROPERTY_ID", "").strip()
    if not prop:
        return {"status": "SKIP", "detail": "GA4_PROPERTY_ID is not set"}
    try:
        svc = build(
            "analyticsadmin",
            "v1beta",
            credentials=creds(["https://www.googleapis.com/auth/analytics.readonly"]),
            cache_discovery=False,
        )
        resp = (
            svc.properties()
            .keyEvents()
            .list(parent=f"properties/{prop}", pageSize=200)
            .execute()
        )
        names = [item.get("eventName") for item in resp.get("keyEvents", [])]
        return {"status": "OK", "property_id": prop, "key_events": names}
    except Exception as exc:  # noqa: BLE001
        return {"status": classify(exc), "detail": str(exc).splitlines()[0][:300]}


def check_ga4_data() -> dict:
    prop = os.getenv("GA4_PROPERTY_ID", "").strip()
    if not prop:
        return {"status": "SKIP", "detail": "GA4_PROPERTY_ID is not set"}
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS_PATH
        client = BetaAnalyticsDataClient()
        end = datetime.now(timezone.utc).date() - timedelta(days=1)
        start = end - timedelta(days=6)
        resp = client.run_report(
            RunReportRequest(
                property=f"properties/{prop}",
                metrics=[Metric(name="sessions")],
                date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
            )
        )
        sessions = resp.rows[0].metric_values[0].value if resp.rows else "0"
        return {"status": "OK", "property_id": prop, "sessions_7d": sessions}
    except Exception as exc:  # noqa: BLE001
        return {"status": classify(exc), "detail": str(exc).splitlines()[0][:300]}


def check_gsc() -> dict:
    site = os.getenv("GSC_SITE_URL", "").strip()
    if not site:
        return {"status": "SKIP", "detail": "GSC_SITE_URL is not set"}
    try:
        svc = build(
            "searchconsole",
            "v1",
            credentials=creds(["https://www.googleapis.com/auth/webmasters.readonly"]),
            cache_discovery=False,
        )
        end = datetime.now(timezone.utc).date() - timedelta(days=3)
        start = end - timedelta(days=7)
        resp = (
            svc.searchanalytics()
            .query(
                siteUrl=site,
                body={"startDate": start.isoformat(), "endDate": end.isoformat(), "rowLimit": 1},
            )
            .execute()
        )
        rows = len(resp.get("rows", []))
        return {"status": "OK", "site_url": site, "sample_rows": rows}
    except Exception as exc:  # noqa: BLE001
        return {"status": classify(exc), "detail": str(exc).splitlines()[0][:300], "site_url": site}


def check_gtm() -> dict:
    try:
        svc = build(
            "tagmanager",
            "v2",
            credentials=creds(["https://www.googleapis.com/auth/tagmanager.readonly"]),
            cache_discovery=False,
        )
        accounts = svc.accounts().list().execute().get("account", [])
        account_id = os.getenv("GTM_ACCOUNT_ID", "").strip()
        container_id = os.getenv("GTM_CONTAINER_ID", "").strip()
        out: dict = {
            "status": "OK",
            "account_count": len(accounts),
            "accounts": [
                {"account_id": a.get("accountId"), "name": a.get("name")} for a in accounts
            ],
            "env_gtm_account_id": account_id or None,
            "env_gtm_container_id": container_id or None,
        }
        if account_id:
            parent = f"accounts/{account_id}"
            containers = (
                svc.accounts().containers().list(parent=parent).execute().get("container", [])
            )
            out["containers"] = [
                {
                    "container_id": c.get("containerId"),
                    "public_id": c.get("publicId"),
                    "name": c.get("name"),
                }
                for c in containers
            ]
        return out
    except Exception as exc:  # noqa: BLE001
        return {"status": classify(exc), "detail": str(exc).splitlines()[0][:300]}


def check_sheets() -> dict:
    sheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
    if not sheet_id:
        return {"status": "SKIP", "detail": "GOOGLE_SHEETS_SPREADSHEET_ID is not set"}
    try:
        import gspread

        client = gspread.authorize(
            creds(
                [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
            )
        )
        book = client.open_by_key(sheet_id)
        titles = [ws.title for ws in book.worksheets()]
        return {"status": "OK", "title": book.title, "worksheets": titles}
    except Exception as exc:  # noqa: BLE001
        return {"status": classify(exc), "detail": str(exc).splitlines()[0][:300]}


def check_gbp() -> dict:
    try:
        import httpx
        from google.auth.transport.requests import Request

        credentials = creds(["https://www.googleapis.com/auth/business.manage"])
        credentials.refresh(Request())
        resp = httpx.get(
            "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=30,
        )
        if resp.status_code == 429:
            return {"status": "429", "detail": "GBP quota / rate limit on accounts.list"}
        if resp.status_code >= 400:
            return {
                "status": str(resp.status_code),
                "detail": resp.text.splitlines()[0][:300] if resp.text else resp.reason_phrase,
            }
        accounts = resp.json().get("accounts", [])
        return {
            "status": "OK",
            "account_count": len(accounts),
            "accounts": [
                {"name": a.get("name"), "accountName": a.get("accountName")} for a in accounts
            ],
            "env_gbp_location_id": os.getenv("GBP_LOCATION_ID", "").strip() or None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": classify(exc), "detail": str(exc).splitlines()[0][:300]}


def ads_env_presence() -> dict:
    keys = [
        "GOOGLE_ADS_CUSTOMER_ID",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
    ]
    present = {key: bool(os.getenv(key, "").strip()) for key in keys}
    ready = all(
        present[key]
        for key in (
            "GOOGLE_ADS_CUSTOMER_ID",
            "GOOGLE_ADS_DEVELOPER_TOKEN",
            "GOOGLE_ADS_REFRESH_TOKEN",
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
        )
    )
    return {
        "direct_api_env_ready": ready,
        "vars_set": present,
        "note": "This does not call Ads. False means GA4-derived pull is still the fallback.",
    }


def main() -> int:
    if not os.path.exists(CREDS_PATH):
        print(json.dumps({"status": "FAIL", "detail": f"missing credentials file: {CREDS_PATH}"}))
        return 1

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "credentials_path_exists": True,
        "ga4_admin": check_ga4_admin(),
        "ga4_data": check_ga4_data(),
        "gsc": check_gsc(),
        "gtm": check_gtm(),
        "sheets": check_sheets(),
        "gbp": check_gbp(),
        "google_ads_env": ads_env_presence(),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
