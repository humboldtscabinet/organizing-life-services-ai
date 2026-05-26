"""Round 3 — generate draft titles + meta descriptions for over-long pages.

Reads the most recent deep audit JSON, finds every page flagged
`title_too_long` or `meta_description_too_long`, and asks Claude to draft
new SEO-compliant replacements.

OUTPUT: data/audit_output/round3_meta_drafts.json

NOTHING is pushed to Shopify by this script. The output is a staging file
that a human reviews. After approval, run `push_meta_round3.py` to deploy
only the entries marked `"approved": true`.

Usage:
    source .venv-audit/bin/activate
    python data/round3_draft_metas.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from anthropic import Anthropic

# ---------- Config ----------
AUDIT_DIR = Path("data/audit_output")
OUTPUT_FILE = AUDIT_DIR / "round3_meta_drafts.json"
MODEL = "claude-sonnet-4-20250514"
TITLE_MAX = 60
TITLE_MIN = 45
META_MAX = 160
META_MIN = 120

# Pages that need special handling (e.g. blog index lives on the Blog object,
# not as a single article metafield). These are still drafted but flagged.
SPECIAL_HANDLES = {
    "/blogs/news": "blog_index — title lives on the Blog object, not metafield. Update via Shopify admin -> Online Store -> Blog Posts -> Manage Blogs.",
}

PROMPT = """You are an SEO copywriter for Organizing Life Services, a Florida
Gulf Coast estate sale & senior downsizing company (primary counties: Pinellas,
Pasco, Hillsborough; also serves Hernando, Citrus, Manatee).

Rewrite the meta title and meta description for this page:

URL:                {url}
PAGE TYPE:          {kind}
CURRENT TITLE:      ({current_title_len} chars) {current_title}
CURRENT H1:         {current_h1}
CURRENT META DESC:  ({current_meta_len} chars) {current_meta}
TOP GSC QUERIES:    {top_queries}

CONSTRAINTS:
- New title: {title_min}-{title_max} characters. Lead with the primary intent /
  keyword. Brand suffix only if it fits (" | Organizing Life Services" is 28 chars).
- New meta description: {meta_min}-{meta_max} characters. Include primary keyword
  naturally, give a concrete reason to click, end with a soft CTA.
- Preserve the page's actual topic — DO NOT invent service areas or claims not
  supported by the current title/H1.
- If the current title is already short enough, return it unchanged but explain
  in `rationale`.

Return STRICT JSON ONLY, no markdown fences, with this exact shape:
{{
  "new_title": "...",
  "new_title_chars": N,
  "new_meta_description": "...",
  "new_meta_chars": N,
  "primary_keyword": "...",
  "rationale": "one sentence on what you changed and why"
}}
"""


# ---------- Helpers ----------
def latest_audit_json() -> Path:
    candidates = sorted(AUDIT_DIR.glob("deep_seo_audit_*.json"), reverse=True)
    if not candidates:
        sys.exit(f"No audit JSON found in {AUDIT_DIR}/")
    return candidates[0]


def url_to_handle_kind(url: str) -> tuple[str, str]:
    """Return (handle, kind) where kind in {'article', 'page', 'special'}."""
    path = urlparse(url).path.rstrip("/")
    if path in SPECIAL_HANDLES:
        return path, "special"
    if path.startswith("/blogs/news/"):
        return path[len("/blogs/news/"):], "article"
    if path.startswith("/pages/"):
        return path[len("/pages/"):], "page"
    return path, "special"


def build_query_map(gsc: dict) -> dict[str, list[tuple[str, int]]]:
    page_q: dict[str, list[tuple[str, int]]] = {}
    for src in ("ctr_opportunities", "striking_distance", "top_query_winners"):
        for item in gsc.get(src, []):
            page = item.get("page") or item.get("url") or ""
            q = item.get("query", "")
            imp = item.get("impressions", 0)
            if page and q:
                page_q.setdefault(page, []).append((q, imp))
    return page_q


def collect_targets(audit: dict) -> list[dict]:
    page_q = build_query_map(audit.get("gsc", {}))
    targets = []
    for p in audit["crawl"]["pages"]:
        issues = p.get("issues") or []
        needs_title = "title_too_long" in issues
        needs_meta = "meta_description_too_long" in issues or "meta_description_too_short" in issues or "missing_meta_description" in issues
        if not (needs_title or needs_meta):
            continue
        url = p["url"]
        handle, kind = url_to_handle_kind(url)
        top_q = sorted(page_q.get(url, []), key=lambda x: -x[1])[:5]
        targets.append({
            "url": url,
            "handle": handle,
            "kind": kind,
            "needs_title_fix": needs_title,
            "needs_meta_fix": needs_meta,
            "current_title": p.get("title") or "",
            "current_title_len": p.get("title_len") or 0,
            "current_meta": p.get("meta_description") or "",
            "current_meta_len": p.get("meta_description_len") or 0,
            "current_h1": p.get("h1_first") or "",
            "top_queries": [{"query": q, "impressions": imp} for q, imp in top_q],
        })
    return targets


def draft_one(client: Anthropic, target: dict) -> dict:
    top_q_str = (
        ", ".join(f"'{q['query']}' ({q['impressions']} impr)" for q in target["top_queries"])
        if target["top_queries"]
        else "(no GSC data — infer from URL/H1)"
    )
    prompt = PROMPT.format(
        url=target["url"],
        kind=target["kind"],
        current_title=target["current_title"],
        current_title_len=target["current_title_len"],
        current_h1=target["current_h1"],
        current_meta=target["current_meta"] or "(none)",
        current_meta_len=target["current_meta_len"],
        top_queries=top_q_str,
        title_min=TITLE_MIN,
        title_max=TITLE_MAX,
        meta_min=META_MIN,
        meta_max=META_MAX,
    )
    msg = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip code fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
        text = text.strip().rstrip("`").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"_parse_error": True, "raw": text}
    return parsed


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set in the environment.")

    audit_file = latest_audit_json()
    print(f"[round3] Using audit: {audit_file.name}")
    with audit_file.open() as f:
        audit = json.load(f)

    targets = collect_targets(audit)
    print(f"[round3] Targets: {len(targets)} pages with title/meta issues")

    client = Anthropic()
    drafts = []
    for i, t in enumerate(targets, 1):
        print(f"[round3] ({i}/{len(targets)}) drafting {t['handle']} ...", flush=True)
        for attempt in range(3):
            try:
                d = draft_one(client, t)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  retry {attempt+1}: {e}")
                time.sleep(2 ** attempt)
        else:
            d = {"_error": "max retries exceeded"}
        drafts.append({
            **t,
            "draft": d,
            "approved": False,
            "special_note": SPECIAL_HANDLES.get(urlparse(t["url"]).path.rstrip("/")),
        })

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps({
        "source_audit": audit_file.name,
        "model": MODEL,
        "count": len(drafts),
        "title_target_chars": [TITLE_MIN, TITLE_MAX],
        "meta_target_chars": [META_MIN, META_MAX],
        "drafts": drafts,
    }, indent=2))
    print(f"\n[round3] Wrote {len(drafts)} drafts to {OUTPUT_FILE}")
    print(f"[round3] Next: review the file, flip `approved: true` on entries to deploy,")
    print(f"[round3]       then run `python data/push_meta_round3.py`.")


if __name__ == "__main__":
    main()
