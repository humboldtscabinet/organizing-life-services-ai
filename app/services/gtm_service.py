"""
Google Tag Manager — Read & Audit Service

Provides read-only access to GTM containers: list workspaces, tags,
triggers, variables, and detect drift / common misconfigurations.

Auth: uses the same service account as GA4/GSC. The service account
email (from credentials/google-service-account.json -> client_email)
must be added as a User in the GTM container UI:

  GTM UI -> Admin -> User Management -> Add user
  Permission level: 'Read' for audit-only, 'Edit' if/when we add writes.

Required env:
  GTM_ACCOUNT_ID    e.g. 6000123456
  GTM_CONTAINER_ID  e.g. 7654321 (the numeric ID, NOT the GTM-XXXX public ID)

The numeric IDs can be found via discover_gtm_accounts() once auth works.
"""
from __future__ import annotations

import os
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

GTM_SCOPES = [
    "https://www.googleapis.com/auth/tagmanager.readonly",
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
]


def _gtm_service():
    """Return an authenticated tagmanager v2 client, or None if not configured."""
    creds_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-service-account.json",
    )
    if not os.path.exists(creds_path):
        return None
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=GTM_SCOPES,
    )
    return build("tagmanager", "v2", credentials=credentials, cache_discovery=False)


def direct_api_available() -> bool:
    """True if GTM service can be built. Does not verify container access."""
    return _gtm_service() is not None


# ===================== Discovery =====================

def discover_gtm_accounts() -> list[dict]:
    """List every GTM account the service account can see."""
    svc = _gtm_service()
    if svc is None:
        raise RuntimeError("GTM service not configured.")
    resp = svc.accounts().list().execute()
    return [
        {"account_id": a["accountId"], "name": a["name"], "path": a["path"]}
        for a in resp.get("account", [])
    ]


def discover_gtm_containers(account_id: str) -> list[dict]:
    """List every container under the given GTM account."""
    svc = _gtm_service()
    if svc is None:
        raise RuntimeError("GTM service not configured.")
    parent = f"accounts/{account_id}"
    resp = svc.accounts().containers().list(parent=parent).execute()
    return [
        {
            "container_id": c["containerId"],
            "public_id": c["publicId"],   # GTM-XXXX
            "name": c["name"],
            "usage_context": c.get("usageContext", []),
            "path": c["path"],
        }
        for c in resp.get("container", [])
    ]


# ===================== Helpers =====================

def _container_path() -> str:
    account_id = os.getenv("GTM_ACCOUNT_ID", "").strip()
    container_id = os.getenv("GTM_CONTAINER_ID", "").strip()
    if not account_id or not container_id:
        raise ValueError(
            "GTM_ACCOUNT_ID and GTM_CONTAINER_ID must be set. "
            "Run discover_gtm_accounts() / discover_gtm_containers() to find them."
        )
    return f"accounts/{account_id}/containers/{container_id}"


def _default_workspace() -> str:
    """Return the path of the 'Default Workspace' for the container."""
    svc = _gtm_service()
    if svc is None:
        raise RuntimeError("GTM service not configured.")
    parent = _container_path()
    resp = svc.accounts().containers().workspaces().list(parent=parent).execute()
    workspaces = resp.get("workspace", [])
    if not workspaces:
        raise RuntimeError(f"No workspaces found under {parent}")
    # Prefer one literally called "Default Workspace"; fall back to first.
    for w in workspaces:
        if w.get("name") == "Default Workspace":
            return w["path"]
    return workspaces[0]["path"]


# ===================== Read =====================

def list_tags() -> list[dict]:
    """Return every tag in the default workspace."""
    svc = _gtm_service()
    if svc is None:
        raise RuntimeError("GTM service not configured.")
    parent = _default_workspace()
    resp = svc.accounts().containers().workspaces().tags().list(parent=parent).execute()
    return [
        {
            "tag_id": t.get("tagId"),
            "name": t.get("name"),
            "type": t.get("type"),
            "firing_trigger_ids": t.get("firingTriggerId", []),
            "blocking_trigger_ids": t.get("blockingTriggerId", []),
            "paused": t.get("paused", False),
            "parameter": t.get("parameter", []),
        }
        for t in resp.get("tag", [])
    ]


def list_triggers() -> list[dict]:
    svc = _gtm_service()
    if svc is None:
        raise RuntimeError("GTM service not configured.")
    parent = _default_workspace()
    resp = svc.accounts().containers().workspaces().triggers().list(parent=parent).execute()
    return [
        {
            "trigger_id": t.get("triggerId"),
            "name": t.get("name"),
            "type": t.get("type"),
            "filter": t.get("filter", []),
        }
        for t in resp.get("trigger", [])
    ]


def list_variables() -> list[dict]:
    svc = _gtm_service()
    if svc is None:
        raise RuntimeError("GTM service not configured.")
    parent = _default_workspace()
    resp = svc.accounts().containers().workspaces().variables().list(parent=parent).execute()
    return [
        {
            "variable_id": v.get("variableId"),
            "name": v.get("name"),
            "type": v.get("type"),
        }
        for v in resp.get("variable", [])
    ]


# ===================== Audit =====================

def audit_container() -> dict:
    """Detect common GTM misconfigurations.

    Heuristics:
      * Tag has no firing trigger -> dead tag.
      * Multiple Google Ads conversion tags fire on the same trigger
        -> potential double-counting.
      * GA4 config tag is paused -> no analytics flowing.
      * Tag named 'page view' / 'pageview' wired to a Google Ads conversion
        -> the bogus-conversion antipattern we cleaned up at the Ads level.
    """
    tags = list_tags()
    triggers = list_triggers()
    trigger_by_id = {t["trigger_id"]: t for t in triggers}

    findings: list[dict] = []

    # Group Ads conversion tags by trigger to spot double-fires.
    ads_by_trigger: dict[str, list[str]] = {}

    for t in tags:
        name_lc = (t["name"] or "").lower()
        type_lc = (t["type"] or "").lower()
        issues: list[str] = []

        if not t["firing_trigger_ids"]:
            issues.append("no firing trigger (dead tag)")

        if t["paused"] and "ga4" in type_lc:
            issues.append("GA4 tag is PAUSED — analytics not flowing")

        if "awct" in type_lc or "google ads" in type_lc or "adwords" in type_lc:
            for tid in t["firing_trigger_ids"]:
                ads_by_trigger.setdefault(tid, []).append(t["name"])
            if any(s in name_lc for s in ("page view", "pageview", "page load")):
                issues.append(
                    "Google Ads conversion tag wired to page-view event "
                    "(creates bogus conversions — same antipattern cleaned up in Ads UI)"
                )

        if issues:
            findings.append({**t, "issues": issues})

    for tid, tag_names in ads_by_trigger.items():
        if len(tag_names) > 1:
            findings.append({
                "trigger_id": tid,
                "trigger_name": trigger_by_id.get(tid, {}).get("name", "?"),
                "tag_names": tag_names,
                "issues": [
                    f"{len(tag_names)} Google Ads conversion tags share this trigger "
                    "(potential double-counting)"
                ],
            })

    return {
        "container_path": _container_path(),
        "tag_count": len(tags),
        "trigger_count": len(triggers),
        "flagged": len(findings),
        "findings": findings,
    }


def get_container_overview() -> dict:
    """Single-call summary of container contents + audit."""
    if not direct_api_available():
        return {"available": False, "reason": "GTM service not configured"}
    try:
        return {
            "available": True,
            "tags": list_tags(),
            "triggers": list_triggers(),
            "variables": list_variables(),
            "audit": audit_container(),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}
