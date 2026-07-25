"""
Google Tag Manager — Read, Audit & Gated Write Service

Read/audit access plus workspace-scoped tag/trigger CRUD, container version
create, and live publish. Publish is high-stakes and must be gated at the
route/script layer (human_confirmed + judge_verdict=PASS).

Auth: same service account as GA4/GSC. Add the SA email in GTM UI:

  GTM UI -> Admin -> User Management -> Add / edit user
  Permission: 'Publish' for live publish (Edit alone cannot publish).

Required env:
  GTM_ACCOUNT_ID    e.g. 6000123456
  GTM_CONTAINER_ID  e.g. 7654321 (numeric ID, NOT GTM-XXXX)

Optional:
  GA4_MEASUREMENT_ID  e.g. G-XXXXXXXX — used for GA4 Event tags when no
                      existing GA4 Config / Google tag can be referenced.

Numeric IDs: discover_gtm_accounts() / discover_gtm_containers().
"""
from __future__ import annotations

import os
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

GTM_SCOPES = [
    "https://www.googleapis.com/auth/tagmanager.readonly",
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
    "https://www.googleapis.com/auth/tagmanager.edit.containerversions",
    "https://www.googleapis.com/auth/tagmanager.publish",
]

# Idempotent OLS phone-click entities
PHONE_TRIGGER_NAME = "OLS - tel link click"
PHONE_TAG_NAME = "OLS - phone_call_clicks"
PHONE_EVENT_NAME = "phone_call_clicks"


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


def _require_svc():
    svc = _gtm_service()
    if svc is None:
        raise RuntimeError("GTM service not configured.")
    return svc


def direct_api_available() -> bool:
    """True if GTM service can be built. Does not verify container access."""
    return _gtm_service() is not None


# ===================== Discovery =====================

def discover_gtm_accounts() -> list[dict]:
    """List every GTM account the service account can see."""
    svc = _require_svc()
    resp = svc.accounts().list().execute()
    return [
        {"account_id": a["accountId"], "name": a["name"], "path": a["path"]}
        for a in resp.get("account", [])
    ]


def discover_gtm_containers(account_id: str) -> list[dict]:
    """List every container under the given GTM account."""
    svc = _require_svc()
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
    svc = _require_svc()
    parent = _container_path()
    resp = svc.accounts().containers().workspaces().list(parent=parent).execute()
    workspaces = resp.get("workspace", [])
    if not workspaces:
        raise RuntimeError(f"No workspaces found under {parent}")
    for w in workspaces:
        if w.get("name") == "Default Workspace":
            return w["path"]
    return workspaces[0]["path"]


def _param(key: str, parameters: list[dict] | None) -> str | None:
    for p in parameters or []:
        if p.get("key") == key:
            return p.get("value")
    return None


def _summarize_tag(t: dict) -> dict:
    return {
        "tag_id": t.get("tagId"),
        "name": t.get("name"),
        "type": t.get("type"),
        "path": t.get("path"),
        "fingerprint": t.get("fingerprint"),
        "firing_trigger_ids": t.get("firingTriggerId", []),
        "blocking_trigger_ids": t.get("blockingTriggerId", []),
        "paused": t.get("paused", False),
        "parameter": t.get("parameter", []),
    }


def _summarize_trigger(t: dict) -> dict:
    return {
        "trigger_id": t.get("triggerId"),
        "name": t.get("name"),
        "type": t.get("type"),
        "path": t.get("path"),
        "fingerprint": t.get("fingerprint"),
        "filter": t.get("filter", []),
    }


# ===================== Read =====================

def list_tags(*, workspace_path: str | None = None) -> list[dict]:
    """Return every tag in the workspace (default workspace if omitted)."""
    svc = _require_svc()
    parent = workspace_path or _default_workspace()
    resp = svc.accounts().containers().workspaces().tags().list(parent=parent).execute()
    return [_summarize_tag(t) for t in resp.get("tag", [])]


def list_triggers(*, workspace_path: str | None = None) -> list[dict]:
    svc = _require_svc()
    parent = workspace_path or _default_workspace()
    resp = svc.accounts().containers().workspaces().triggers().list(parent=parent).execute()
    return [_summarize_trigger(t) for t in resp.get("trigger", [])]


def list_variables(*, workspace_path: str | None = None) -> list[dict]:
    svc = _require_svc()
    parent = workspace_path or _default_workspace()
    resp = svc.accounts().containers().workspaces().variables().list(parent=parent).execute()
    return [
        {
            "variable_id": v.get("variableId"),
            "name": v.get("name"),
            "type": v.get("type"),
        }
        for v in resp.get("variable", [])
    ]


def get_tag_by_name(name: str, *, workspace_path: str | None = None) -> dict | None:
    for tag in list_tags(workspace_path=workspace_path):
        if tag.get("name") == name:
            return tag
    return None


def get_trigger_by_name(name: str, *, workspace_path: str | None = None) -> dict | None:
    for trigger in list_triggers(workspace_path=workspace_path):
        if trigger.get("name") == name:
            return trigger
    return None


# ===================== Write: triggers / tags =====================

def _tel_link_trigger_body(name: str = PHONE_TRIGGER_NAME) -> dict[str, Any]:
    return {
        "name": name,
        "type": "linkClick",
        "filter": [
            {
                "type": "contains",
                "parameter": [
                    {"type": "template", "key": "arg0", "value": "{{Click URL}}"},
                    {"type": "template", "key": "arg1", "value": "tel:"},
                ],
            }
        ],
        "waitForTags": {"type": "boolean", "value": "false"},
        "checkValidation": {"type": "boolean", "value": "false"},
        "waitForTagsTimeout": {"type": "integer", "value": "2000"},
    }


def create_trigger(
    body: dict[str, Any],
    *,
    workspace_path: str | None = None,
) -> dict:
    """Create a trigger in the workspace. ``body`` is a GTM Trigger resource."""
    svc = _require_svc()
    parent = workspace_path or _default_workspace()
    created = (
        svc.accounts()
        .containers()
        .workspaces()
        .triggers()
        .create(parent=parent, body=body)
        .execute()
    )
    return _summarize_trigger(created)


def update_trigger(
    trigger_path: str,
    body: dict[str, Any],
    *,
    fingerprint: str | None = None,
) -> dict:
    """Update an existing trigger. Pass fingerprint when available."""
    svc = _require_svc()
    kwargs: dict[str, Any] = {"path": trigger_path, "body": body}
    if fingerprint:
        kwargs["fingerprint"] = fingerprint
    updated = (
        svc.accounts()
        .containers()
        .workspaces()
        .triggers()
        .update(**kwargs)
        .execute()
    )
    return _summarize_trigger(updated)


def create_tag(
    body: dict[str, Any],
    *,
    workspace_path: str | None = None,
) -> dict:
    """Create a tag in the workspace. ``body`` is a GTM Tag resource."""
    svc = _require_svc()
    parent = workspace_path or _default_workspace()
    created = (
        svc.accounts()
        .containers()
        .workspaces()
        .tags()
        .create(parent=parent, body=body)
        .execute()
    )
    return _summarize_tag(created)


def update_tag(
    tag_path: str,
    body: dict[str, Any],
    *,
    fingerprint: str | None = None,
) -> dict:
    """Update an existing tag. Pass fingerprint when available."""
    svc = _require_svc()
    kwargs: dict[str, Any] = {"path": tag_path, "body": body}
    if fingerprint:
        kwargs["fingerprint"] = fingerprint
    updated = (
        svc.accounts()
        .containers()
        .workspaces()
        .tags()
        .update(**kwargs)
        .execute()
    )
    return _summarize_tag(updated)


def _looks_like_ga4_measurement_id(value: str | None) -> bool:
    return bool(value) and value.strip().upper().startswith("G-")


def _tag_measurement_hint(tag: dict) -> str | None:
    """Return a GA4 G- ID or config tag name hint from a tag resource."""
    params = tag.get("parameter") or []
    for key in (
        "measurementIdOverride",
        "measurementId",
        "tagId",
        "measurement_id",
    ):
        value = _param(key, params)
        if _looks_like_ga4_measurement_id(value):
            return value
    name = tag.get("name") or ""
    if _looks_like_ga4_measurement_id(name):
        return name
    return None


def _resolve_measurement_params(tags: list[dict]) -> list[dict]:
    """Build GA4 Event measurement parameters from existing config or env.

    Prefer real GA4 ``G-`` streams over Google Ads ``AW-`` Google tags.
    """
    env_measurement = os.getenv("GA4_MEASUREMENT_ID", "").strip()
    if _looks_like_ga4_measurement_id(env_measurement):
        return [
            {
                "type": "template",
                "key": "measurementIdOverride",
                "value": env_measurement,
            }
        ]

    ga4_config = next(
        (t for t in tags if (t.get("type") or "").lower() == "gaawc"),
        None,
    )
    if ga4_config:
        return [
            {
                "type": "tagReference",
                "key": "measurementId",
                "value": ga4_config["name"],
            }
        ]

    for tag in tags:
        type_lc = (tag.get("type") or "").lower()
        if type_lc != "googtag":
            continue
        hint = _tag_measurement_hint(tag)
        if hint or "G-" in (tag.get("name") or "").upper():
            return [
                {
                    "type": "tagReference",
                    "key": "measurementId",
                    "value": tag["name"],
                }
            ]

    for tag in tags:
        if (tag.get("type") or "").lower() != "gaawe":
            continue
        ref = _param("measurementId", tag.get("parameter"))
        if ref and "AW-" not in ref.upper():
            return [
                {
                    "type": "tagReference",
                    "key": "measurementId",
                    "value": ref,
                }
            ]
        override = _param("measurementIdOverride", tag.get("parameter"))
        if _looks_like_ga4_measurement_id(override):
            return [
                {
                    "type": "template",
                    "key": "measurementIdOverride",
                    "value": override,
                }
            ]

    if env_measurement:
        return [
            {
                "type": "template",
                "key": "measurementIdOverride",
                "value": env_measurement,
            }
        ]

    raise ValueError(
        "Cannot resolve GA4 measurement ID. Set GA4_MEASUREMENT_ID to a G- ID "
        "(GA4 Admin → Data streams), or ensure a GA4 Config / Google tag for "
        "the G- stream exists in the container. Ads AW- Google tags are not used."
    )


def _phone_event_tag_body(
    *,
    firing_trigger_id: str,
    measurement_params: list[dict],
    name: str = PHONE_TAG_NAME,
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "gaawe",
        "parameter": [
            {"type": "boolean", "key": "sendEcommerceData", "value": "false"},
            {"type": "template", "key": "eventName", "value": PHONE_EVENT_NAME},
            *measurement_params,
        ],
        "firingTriggerId": [str(firing_trigger_id)],
        "paused": False,
    }


def _trigger_has_tel_filter(trigger: dict) -> bool:
    for condition in trigger.get("filter") or []:
        if (condition.get("type") or "").lower() != "contains":
            continue
        params = {p.get("key"): p.get("value") for p in condition.get("parameter") or []}
        arg0 = (params.get("arg0") or "").lower()
        arg1 = (params.get("arg1") or "").lower()
        if "click url" in arg0 and "tel:" in arg1:
            return True
    return False


def _tag_matches_phone_event(tag: dict, expected_trigger_id: str | None) -> bool:
    if (tag.get("type") or "").lower() != "gaawe":
        return False
    if _param("eventName", tag.get("parameter")) != PHONE_EVENT_NAME:
        return False
    if expected_trigger_id is None:
        return True
    firing = {str(x) for x in tag.get("firing_trigger_ids") or []}
    return str(expected_trigger_id) in firing and not tag.get("paused")


# ===================== Versions / publish =====================

def create_version(
    name: str,
    notes: str = "",
    *,
    workspace_path: str | None = None,
) -> dict:
    """Create a container version from the workspace (does not publish live).

    Note: GTM deletes the workspace after version create and returns
    ``new_workspace_path`` for the replacement Default Workspace.
    """
    svc = _require_svc()
    path = workspace_path or _default_workspace()
    resp = (
        svc.accounts()
        .containers()
        .workspaces()
        .create_version(
            path=path,
            body={"name": name, "notes": notes or ""},
        )
        .execute()
    )
    version = resp.get("containerVersion") or {}
    return {
        "version_id": version.get("containerVersionId"),
        "version_path": version.get("path"),
        "name": version.get("name"),
        "notes": version.get("notes"),
        "compiler_error": bool(resp.get("compilerError")),
        "new_workspace_path": resp.get("newWorkspacePath"),
        "sync_status": resp.get("syncStatus"),
        "raw": resp,
    }


def publish_version(version_path: str) -> dict:
    """Publish a container version live. High stakes — gate at the caller."""
    if not version_path or "/versions/" not in version_path:
        raise ValueError(
            "version_path must look like "
            "accounts/{account}/containers/{container}/versions/{version}"
        )
    svc = _require_svc()
    resp = (
        svc.accounts()
        .containers()
        .versions()
        .publish(path=version_path)
        .execute()
    )
    version = resp.get("containerVersion") or {}
    return {
        "status": "published",
        "version_id": version.get("containerVersionId"),
        "version_path": version.get("path") or version_path,
        "name": version.get("name"),
        "raw": resp,
    }


# ===================== Idempotent phone clicks =====================

def ensure_phone_call_clicks_tracking(
    *,
    dry_run: bool = True,
    create_version_after: bool = False,
    version_name: str | None = None,
    version_notes: str = "",
    workspace_path: str | None = None,
) -> dict:
    """Idempotently ensure tel: link click → GA4 ``phone_call_clicks`` event.

    Returns a dry-run-friendly plan::

        {
          "status": "ok",
          "dry_run": true|false,
          "trigger": {"action": "would_create"|"unchanged"|"updated"|"created", ...},
          "tag": {"action": "...", ...},
          "version": {...} | None,
          "would_create": [...],
          "unchanged": [...],
          "updated": [...],
        }
    """
    workspace = workspace_path or _default_workspace()
    tags = list_tags(workspace_path=workspace)
    triggers = list_triggers(workspace_path=workspace)

    would_create: list[str] = []
    unchanged: list[str] = []
    updated: list[str] = []
    created: list[str] = []

    existing_trigger = next(
        (t for t in triggers if t.get("name") == PHONE_TRIGGER_NAME),
        None,
    )
    trigger_plan: dict[str, Any]
    trigger_id: str | None = None

    if existing_trigger and _trigger_has_tel_filter(existing_trigger):
        trigger_id = str(existing_trigger["trigger_id"])
        trigger_plan = {
            "action": "unchanged",
            "name": PHONE_TRIGGER_NAME,
            "trigger_id": trigger_id,
            "path": existing_trigger.get("path"),
        }
        unchanged.append(f"trigger:{PHONE_TRIGGER_NAME}")
    elif existing_trigger:
        trigger_id = str(existing_trigger["trigger_id"])
        body = _tel_link_trigger_body()
        if dry_run:
            trigger_plan = {
                "action": "would_update",
                "name": PHONE_TRIGGER_NAME,
                "trigger_id": trigger_id,
                "path": existing_trigger.get("path"),
                "body": body,
            }
            updated.append(f"trigger:{PHONE_TRIGGER_NAME}")
        else:
            result = update_trigger(
                existing_trigger["path"],
                body,
                fingerprint=existing_trigger.get("fingerprint"),
            )
            trigger_id = str(result["trigger_id"])
            trigger_plan = {
                "action": "updated",
                "name": PHONE_TRIGGER_NAME,
                "trigger_id": trigger_id,
                "path": result.get("path"),
            }
            updated.append(f"trigger:{PHONE_TRIGGER_NAME}")
    else:
        body = _tel_link_trigger_body()
        if dry_run:
            trigger_plan = {
                "action": "would_create",
                "name": PHONE_TRIGGER_NAME,
                "body": body,
            }
            would_create.append(f"trigger:{PHONE_TRIGGER_NAME}")
        else:
            result = create_trigger(body, workspace_path=workspace)
            trigger_id = str(result["trigger_id"])
            trigger_plan = {
                "action": "created",
                "name": PHONE_TRIGGER_NAME,
                "trigger_id": trigger_id,
                "path": result.get("path"),
            }
            created.append(f"trigger:{PHONE_TRIGGER_NAME}")

    # Re-list tags after potential trigger create so measurement resolution is fresh.
    if not dry_run and trigger_plan["action"] in {"created", "updated"}:
        tags = list_tags(workspace_path=workspace)

    measurement_params = _resolve_measurement_params(tags)
    existing_tag = next((t for t in tags if t.get("name") == PHONE_TAG_NAME), None)

    # For dry-run create of both, we may not have a real trigger_id yet.
    planned_trigger_id = trigger_id or "PENDING_CREATE"

    tag_plan: dict[str, Any]
    if existing_tag and _tag_matches_phone_event(existing_tag, trigger_id):
        tag_plan = {
            "action": "unchanged",
            "name": PHONE_TAG_NAME,
            "tag_id": existing_tag.get("tag_id"),
            "path": existing_tag.get("path"),
            "event_name": PHONE_EVENT_NAME,
        }
        unchanged.append(f"tag:{PHONE_TAG_NAME}")
    elif existing_tag:
        body = _phone_event_tag_body(
            firing_trigger_id=planned_trigger_id,
            measurement_params=measurement_params,
        )
        if dry_run or trigger_id is None:
            tag_plan = {
                "action": "would_update",
                "name": PHONE_TAG_NAME,
                "tag_id": existing_tag.get("tag_id"),
                "path": existing_tag.get("path"),
                "body": body,
            }
            updated.append(f"tag:{PHONE_TAG_NAME}")
        else:
            result = update_tag(
                existing_tag["path"],
                body,
                fingerprint=existing_tag.get("fingerprint"),
            )
            tag_plan = {
                "action": "updated",
                "name": PHONE_TAG_NAME,
                "tag_id": result.get("tag_id"),
                "path": result.get("path"),
                "event_name": PHONE_EVENT_NAME,
            }
            updated.append(f"tag:{PHONE_TAG_NAME}")
    else:
        body = _phone_event_tag_body(
            firing_trigger_id=planned_trigger_id,
            measurement_params=measurement_params,
        )
        if dry_run or trigger_id is None:
            tag_plan = {
                "action": "would_create",
                "name": PHONE_TAG_NAME,
                "body": body,
            }
            would_create.append(f"tag:{PHONE_TAG_NAME}")
        else:
            result = create_tag(body, workspace_path=workspace)
            tag_plan = {
                "action": "created",
                "name": PHONE_TAG_NAME,
                "tag_id": result.get("tag_id"),
                "path": result.get("path"),
                "event_name": PHONE_EVENT_NAME,
            }
            created.append(f"tag:{PHONE_TAG_NAME}")

    version_plan: dict[str, Any] | None = None
    # Create a version when requested (even if entities unchanged — snapshot).
    if create_version_after:
        vname = version_name or f"OLS phone_call_clicks {PHONE_EVENT_NAME}"
        vnotes = version_notes or (
            "Workspace snapshot after ensuring OLS phone_call_clicks tracking."
        )
        if dry_run:
            version_plan = {
                "action": "would_create_version",
                "name": vname,
                "notes": vnotes,
            }
            would_create.append(f"version:{vname}")
        else:
            version_plan = {
                "action": "created_version",
                **create_version(vname, vnotes, workspace_path=workspace),
            }
            created.append(f"version:{version_plan.get('version_id')}")

    if dry_run:
        status = "dry_run"
    elif created or updated:
        status = "applied"
    else:
        status = "unchanged"

    return {
        "status": status,
        "dry_run": dry_run,
        "workspace_path": workspace,
        "container_path": _container_path(),
        "trigger": trigger_plan,
        "tag": tag_plan,
        "version": version_plan,
        "would_create": would_create,
        "unchanged": unchanged,
        "updated": updated,
        "created": created,
        "publish_required": True,
        "note": (
            "Workspace/version only — call publish_version separately after "
            "human_confirmed + judge_verdict=PASS."
        ),
    }


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
