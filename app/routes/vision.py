"""
Vision Routes — AI image recognition endpoints for estate sale photos.

All endpoints are manual-trigger:
- Pull image URLs from Shopify
- Analyze images with Claude Vision
- Export results as CSV for XO Gallery bulk upload
"""

import json
import logging
import os
import threading
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db
from app.route_errors import raise_route_error
from app.runtime_config import is_production_env
from app.safety import require_high_stakes_confirmation
from app.services.vision_service import (
    analyze_gallery_images,
    bulk_analyze_with_budget,
    bulk_push_alt_text,
    compare_alt_text,
    export_analysis_csv,
    fix_empty_alt_text,
    get_analysis_summary,
    list_all_themes,
    pull_gallery_images_from_page,
    pull_image_urls,
    pull_theme_assets,
    pull_xo_gallery_assets,
)

router = APIRouter(prefix="/api/vision", tags=["Vision AI"])
logger = logging.getLogger(__name__)


def require_vision_debug_tools_enabled() -> None:
    """Keep temporary/token-bearing vision utilities out of production."""
    if is_production_env():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vision debug tools are disabled in production",
        )

    enabled = os.getenv("ENABLE_VISION_DEBUG_TOOLS", "").strip().lower()
    if enabled not in {"1", "true", "yes"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vision debug tools are disabled",
        )


def _require_allowed_xo_proxy_url(target_url: str) -> None:
    parsed = urlparse(target_url)
    allowed_hosts = {"gallery.xopify.com"}
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="XO proxy target is not allowed",
        )


@router.get("/images")
def list_shopify_images(limit: int = 50):
    """
    Pull image URLs from Shopify Files API.

    Returns image URLs, filenames, and existing alt text.
    """
    try:
        images = pull_image_urls(limit=limit)
        return {
            "status": "success",
            "count": len(images),
            "images": images,
        }
    except Exception as e:
        raise_route_error(logger, "List Shopify images", e)


@router.get("/images/theme")
def list_theme_images(filter_prefix: str = "photo", limit: int = 250):
    """
    Pull image URLs from Shopify Theme Assets.

    XO Gallery stores estate sale photos as theme assets.
    filter_prefix: filter filenames starting with this (default: "photo")
    """
    try:
        images = pull_theme_assets(filter_prefix=filter_prefix, limit=limit)
        return {
            "status": "success",
            "count": len(images),
            "images": images,
        }
    except Exception as e:
        raise_route_error(logger, "List Shopify theme images", e)


@router.get("/images/page/{page_handle}")
def list_page_images(page_handle: str):
    """
    Pull image URLs embedded in a specific Shopify page.

    Useful for finding XO Gallery images on a particular estate sale page.
    """
    try:
        images = pull_gallery_images_from_page(page_handle)
        return {
            "status": "success",
            "page_handle": page_handle,
            "count": len(images),
            "images": images,
        }
    except Exception as e:
        raise_route_error(logger, "List Shopify page images", e)


@router.get("/themes")
def list_themes():
    """
    List all Shopify themes.

    XO Gallery stores images under an older theme (e.g., theme 7)
    while the storefront uses the active/main theme.
    """
    try:
        themes = list_all_themes()
        return {
            "status": "success",
            "count": len(themes),
            "themes": [
                {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "role": t.get("role"),
                    "created_at": t.get("created_at"),
                }
                for t in themes
            ],
        }
    except Exception as e:
        raise_route_error(logger, "List Shopify themes", e)


@router.get("/images/xo-gallery")
def list_xo_gallery_images(
    theme_id: int = None,
    filter_prefix: str = "photo",
    limit: int = 10000,
):
    """
    Pull XO Gallery image URLs from Shopify theme assets.

    If theme_id is not provided, searches ALL themes for photo assets.
    This is the key endpoint for finding estate sale photos that
    XO Gallery stores under older theme versions.

    Use /api/vision/themes first to find the correct theme_id.
    """
    try:
        images = pull_xo_gallery_assets(
            theme_id=theme_id,
            filter_prefix=filter_prefix,
            limit=limit,
        )
        return {
            "status": "success",
            "count": len(images),
            "images": images,
        }
    except Exception as e:
        raise_route_error(logger, "List XO Gallery images", e)


XO_GALLERY_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "xo_gallery_images.json",
)


@router.post("/images/xo-gallery/import")
async def import_xo_gallery_data(request: Request):
    """
    Import XO Gallery image data from browser crawler.

    Accepts JSON payload with gallery data extracted from the live site.
    Saves to data/xo_gallery_images.json for use by the vision pipeline.

    POST body: {galleries: {gid: {title, name, count, filenames: [...]}}, ...}
    """
    try:
        body = await request.json()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(XO_GALLERY_DATA_FILE), exist_ok=True)

        # Add metadata
        from datetime import datetime

        body["imported_at"] = datetime.utcnow().isoformat()
        body["base_url"] = (
            "https://cdn.shopify.com/s/files/1/0294/7966/5708/t/7/assets/"
        )

        # Count totals
        total_galleries = len(body.get("galleries", {}))
        total_images = sum(
            g.get("count", len(g.get("filenames", [])))
            for g in body.get("galleries", {}).values()
        )

        body["total_galleries"] = total_galleries
        body["total_images"] = total_images

        with open(XO_GALLERY_DATA_FILE, "w") as f:
            json.dump(body, f, indent=2)

        return {
            "status": "success",
            "message": f"Imported {total_galleries} galleries, {total_images} images",
            "file": XO_GALLERY_DATA_FILE,
        }
    except Exception as e:
        raise_route_error(logger, "Import XO Gallery data", e)


@router.get("/images/xo-gallery/local")
def list_local_xo_gallery_images(gallery_id: str = None, limit: int = 100):
    """
    List XO Gallery images from the locally saved JSON file.

    Use gallery_id to filter to a specific gallery.
    Returns image URLs constructed from base_url + filename.
    """
    try:
        if not os.path.exists(XO_GALLERY_DATA_FILE):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No local XO Gallery data. Use POST /images/xo-gallery/import first.",
            )

        with open(XO_GALLERY_DATA_FILE) as f:
            data = json.load(f)

        base_url = data.get("base_url", "")
        galleries = data.get("galleries", {})

        if gallery_id:
            galleries = {gallery_id: galleries.get(gallery_id, {})}

        images = []
        for gid, gallery in galleries.items():
            for fname in gallery.get("filenames", []):
                images.append(
                    {
                        "url": base_url + fname,
                        "filename": fname,
                        "gallery_id": gid,
                        "gallery_title": gallery.get("title", ""),
                        "gallery_name": gallery.get("name", ""),
                    }
                )
                if len(images) >= limit:
                    break
            if len(images) >= limit:
                break

        return {
            "status": "success",
            "total_available": data.get("total_images", 0),
            "returned": len(images),
            "images": images,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise_route_error(logger, "List local XO Gallery images", e)


@router.post("/analyze")
def analyze_images(
    gallery_name: str = "",
    source: str = "files",
    page_handle: str = "",
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Analyze estate sale images with Claude Vision AI.

    source options:
      - "files": Pull from Shopify Files API (default)
      - "theme": Pull from Shopify Theme Assets (active theme)
      - "xo-gallery": Pull from XO Gallery theme assets (searches all themes)
      - "local": Pull from locally saved XO Gallery data (crawled from live site)
      - "page": Pull from a specific page's body HTML

    gallery_name: estate sale name for context (e.g. "2829 Tangelo Way, Palm Harbor")
    limit: max images to analyze (controls API cost, default 10)

    This is a WRITE operation that calls the Anthropic API.
    Each image costs ~$0.01-0.05 depending on size.
    """
    try:
        if source == "xo-gallery":
            images = pull_xo_gallery_assets(
                filter_prefix="photo", limit=limit
            )
        elif source == "local":
            # Load from locally saved XO Gallery data
            if not os.path.exists(XO_GALLERY_DATA_FILE):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No local data. Import first via POST /images/xo-gallery/import",
                )
            with open(XO_GALLERY_DATA_FILE) as f:
                local_data = json.load(f)
            base_url = local_data.get("base_url", "")
            images = []
            for _gid, gallery in local_data.get("galleries", {}).items():
                for fname in gallery.get("filenames", []):
                    images.append(
                        {
                            "url": base_url + fname,
                            "filename": fname,
                            "gallery_name": gallery.get("name", ""),
                        }
                    )
                    if len(images) >= limit:
                        break
                if len(images) >= limit:
                    break
        elif source == "theme":
            images = pull_theme_assets(filter_prefix="photo", limit=limit)
        elif source == "page" and page_handle:
            images = pull_gallery_images_from_page(page_handle)
        else:
            images = pull_image_urls(limit=limit)

        if not images:
            return {
                "status": "warning",
                "detail": "No images found to analyze.",
            }

        result = analyze_gallery_images(
            db=db,
            image_urls=images,
            gallery_name=gallery_name,
            batch_size=limit,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise_route_error(logger, "Analyze images", e)


@router.post("/analyze/bulk")
def bulk_analyze(
    budget: float = 90.0,
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Bulk analyze ALL XO Gallery images from local data with budget cap.

    Processes all 53 galleries (9,183 images) from xo_gallery_images.json.
    Tracks API token usage and cost per image, stopping at the budget limit.

    budget: max spend in USD (default $90)

    This is a LONG-RUNNING operation (~2-4 hours for 9K images).
    Results are committed to DB every 25 images to avoid data loss.
    """
    require_high_stakes_confirmation(
        task_type="vision_bulk_analysis",
        human_confirmed=human_confirmed,
        judge_verdict=judge_verdict,
    )
    try:
        result = bulk_analyze_with_budget(
            db=db,
            budget_dollars=budget,
        )
        return result
    except Exception as e:
        raise_route_error(logger, "Bulk analyze images", e)


# Global status tracker for background alt text push
_alt_push_status = {"running": False, "result": None}


def _run_alt_push_background(force: bool):
    """Run alt text push in a background thread with its own DB session."""
    global _alt_push_status
    _alt_push_status = {"running": True, "result": None, "progress": {}}

    def progress_callback(stats):
        _alt_push_status["progress"] = stats

    try:
        db = SessionLocal()
        result = bulk_push_alt_text(db=db, force=force, progress_callback=progress_callback)
        db.close()
        _alt_push_status = {"running": False, "result": result}
    except Exception as e:
        _alt_push_status = {"running": False, "result": {"status": "error", "detail": str(e)}}


@router.post("/push-alt-text")
def push_alt_text_to_shopify(
    force: bool = False,
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
):
    """
    Bulk push AI-generated alt text to Shopify Files (background job).

    Matches analyzed images by filename to Shopify Files and updates
    the alt text field. Returns immediately — check status via GET /push-alt-text/status.

    By default, skips files with real alt text (but overwrites filename-based
    alt text from tools like Webrex). Set force=true to overwrite everything.
    """
    require_high_stakes_confirmation(
        task_type="bulk_alt_text_push",
        human_confirmed=human_confirmed,
        judge_verdict=judge_verdict,
    )
    global _alt_push_status
    if _alt_push_status.get("running"):
        return {"status": "already_running", "detail": "Alt text push is already in progress. Check /push-alt-text/status"}

    thread = threading.Thread(target=_run_alt_push_background, args=(force,), daemon=True)
    thread.start()
    return {"status": "started", "detail": "Alt text push started in background. Check /push-alt-text/status for progress."}


@router.get("/push-alt-text/status")
def get_push_status():
    """Check the status of a running alt text push job."""
    return _alt_push_status


_fix_empty_status = {"running": False, "result": None, "progress": {}}


def _run_fix_empty_background():
    global _fix_empty_status
    _fix_empty_status = {"running": True, "result": None, "progress": {}}

    def progress_callback(stats):
        _fix_empty_status["progress"] = stats

    try:
        result = fix_empty_alt_text(progress_callback=progress_callback)
        _fix_empty_status = {"running": False, "result": result}
    except Exception as e:
        _fix_empty_status = {"running": False, "result": {"status": "error", "detail": str(e)}}


@router.post("/fix-empty-alt")
def start_fix_empty_alt(
    human_confirmed: bool = False,
    judge_verdict: str | None = None,
):
    """
    Find all Shopify files with empty alt text, analyze them with Claude Vision,
    and push AI-generated alt text. Runs in background.
    """
    require_high_stakes_confirmation(
        task_type="bulk_alt_text_push",
        human_confirmed=human_confirmed,
        judge_verdict=judge_verdict,
    )
    import threading

    if _fix_empty_status.get("running"):
        return {"status": "already_running", "detail": "Fix is already in progress. Check /fix-empty-alt/status"}

    thread = threading.Thread(target=_run_fix_empty_background, daemon=True)
    thread.start()
    return {"status": "started", "detail": "Empty alt text fix started. Check /fix-empty-alt/status for progress."}


@router.get("/fix-empty-alt/status")
def get_fix_empty_status():
    """Check the status of a running fix-empty-alt job."""
    return _fix_empty_status


@router.get("/compare-alt-text")
def compare_alt_text_quality(
    sample_size: int = 10,
    db: Session = Depends(get_db),
):
    """
    Compare existing Shopify alt text (from Webrex/other tools) with our AI-generated alt text.

    Returns side-by-side comparison for matched files so you can evaluate quality.
    """
    try:
        result = compare_alt_text(db=db, sample_size=sample_size)
        return result
    except Exception as e:
        raise_route_error(logger, "Compare alt text", e)


@router.get("/results")
def get_results(db: Session = Depends(get_db)):
    """Get a summary of all image analysis results."""
    try:
        summary = get_analysis_summary(db)
        return {"status": "success", **summary}
    except Exception as e:
        raise_route_error(logger, "Get image analysis results", e)


@router.get("/debug/test-mutation")
def debug_test_mutation(
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """
    Test a single Shopify fileUpdate mutation and return the FULL raw response.

    This helps diagnose why mutations are failing (permissions, scope, format, etc.).
    Fetches the first image file and tries to set its alt text.
    """
    import httpx as _httpx

    from app.services.vision_service import _fetch_shopify_file_ids

    try:
        # Step 1: Get the token info
        from app.services.shopify_service import _get_access_token
        token = _get_access_token()
        # Step 2: Fetch one file
        page = _fetch_shopify_file_ids(limit=1)
        if not page["files"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No files found")

        file_info = page["files"][0]
        file_id = file_info["id"]
        filename = file_info["filename"]
        current_alt = file_info["current_alt"]

        # Step 3: Try the mutation and capture FULL response
        store = os.getenv("SHOPIFY_STORE")
        version = os.getenv("SHOPIFY_API_VERSION", "2024-10")
        url = f"https://{store}.myshopify.com/admin/api/{version}/graphql.json"

        mutation = """
        mutation fileUpdate($input: [FileUpdateInput!]!) {
            fileUpdate(files: $input) {
                files {
                    ... on MediaImage {
                        id
                        alt
                        image {
                            altText
                        }
                    }
                }
                userErrors {
                    field
                    message
                    code
                }
            }
        }
        """
        test_alt = current_alt if current_alt else f"Test alt text for {filename}"
        variables = {
            "input": [{
                "id": file_id,
                "alt": test_alt,
            }]
        }

        resp = _httpx.post(
            url,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            json={"query": mutation, "variables": variables},
            timeout=30,
        )

        return {
            "status": "diagnostic",
            "file_id": file_id,
            "filename": filename,
            "current_alt": current_alt,
            "test_alt_text": test_alt,
            "http_status": resp.status_code,
            "raw_response": resp.json(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise_route_error(logger, "Vision debug mutation test", e)


@router.get("/debug/alt-text-audit")
def debug_alt_text_audit(
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """
    Scan all Shopify files and count how many have empty vs non-empty alt text.
    Returns counts and a sample of files with empty alt text.
    """
    from app.services.vision_service import _fetch_shopify_file_ids

    try:
        empty_alt = []
        has_alt = 0
        total = 0
        cursor = None

        while True:
            page = _fetch_shopify_file_ids(cursor=cursor)
            for f in page["files"]:
                total += 1
                current = f["current_alt"] or ""
                if not current.strip():
                    empty_alt.append({"filename": f["filename"], "id": f["id"]})
                else:
                    has_alt += 1

            if not page["has_next"]:
                break
            cursor = page["cursor"]

        return {
            "total_files": total,
            "has_alt_text": has_alt,
            "empty_alt_text": len(empty_alt),
            "coverage_pct": round(has_alt / total * 100, 1) if total else 0,
            "empty_sample": empty_alt[:25],
        }
    except Exception as e:
        raise_route_error(logger, "Vision debug alt-text audit", e)


@router.get("/errors")
def get_errors(limit: int = 10, db: Session = Depends(get_db)):
    """Get sample error records to diagnose failures."""
    from app.db.models import ImageAnalysis

    errors = (
        db.query(ImageAnalysis)
        .filter(ImageAnalysis.status == "error")
        .limit(limit)
        .all()
    )
    return {
        "count": len(errors),
        "errors": [
            {
                "filename": e.filename,
                "url": e.image_url,
                "error": e.data.get("error", "") if e.data else "",
            }
            for e in errors
        ],
    }


@router.get("/export/csv")
def export_csv(
    gallery_name: str = None,
    db: Session = Depends(get_db),
):
    """
    Export image analysis results as CSV.

    Columns: filename, image_url, title, alt_text, tags, description, confidence

    The CSV can be used for:
    - XO Gallery bulk SEO field updates
    - Google Sheets import for review
    - Bulk alt text updates via Shopify
    """
    try:
        csv_content = export_analysis_csv(db, gallery_name=gallery_name)
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=image_analysis.csv"
            },
        )
    except Exception as e:
        raise_route_error(logger, "Export image analysis CSV", e)


@router.get("/gallery-structure")
def get_gallery_structure():
    """Return xo_gallery_images.json for browser-side XLSX building."""
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "xo_gallery_images.json")
    json_path = os.path.normpath(json_path)
    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gallery JSON not found at {json_path}",
        )
    with open(json_path, "r") as f:
        return json.load(f)


@router.post("/save-file")
async def save_file(
    request: Request,
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """Save uploaded base64 file to data directory."""
    import base64
    body = await request.json()
    filename = body.get("filename", "output.xlsx")
    b64data = body.get("data", "")
    if not b64data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data provided")
    file_bytes = base64.b64decode(b64data)
    save_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", filename)
    save_path = os.path.normpath(save_path)
    with open(save_path, "wb") as f:
        f.write(file_bytes)
    return {"status": "ok", "path": save_path, "size": len(file_bytes)}


@router.get("/store-token")
def store_token(
    t: str = "",
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """Store a session token sent via image beacon from the Shopify admin page."""
    if not t:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No token")
    token_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "xo_session_token.txt")
    token_path = os.path.normpath(token_path)
    with open(token_path, "w") as f:
        f.write(t)
    import base64

    from fastapi.responses import Response
    pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
    return Response(content=pixel, media_type="image/png")


@router.get("/get-token")
def get_stored_token(
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """Return XO Gallery session token status without exposing the token."""
    import base64 as b64
    import time
    token_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "xo_session_token.txt")
    token_path = os.path.normpath(token_path)
    if not os.path.exists(token_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No token stored")
    with open(token_path, "r") as f:
        token = f.read().strip()
    parts = token.split(".")
    if len(parts) == 3:
        padded = parts[1] + "=="
        payload = b64.b64decode(padded)
        payload_json = json.loads(payload)
        exp = payload_json.get("exp", 0)
        now = int(time.time())
        return {"status": "ok", "present": True, "exp": exp, "now": now, "expired": now > exp}
    return {"status": "ok", "present": True, "expired": None}


@router.post("/xo-proxy")
async def xo_proxy(
    request: Request,
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """
    Server-side proxy for XO Gallery API calls.
    Atomic login+fetch: logs in with token, captures cookies, immediately fetches data.
    Body: { "url": "...", "method": "GET"|"POST"|"PUT"|"PATCH",
            "token": "...", "body": {...}, "login": true/false,
            "params": {"hmac": "...", "session": "...", "timestamp": "..."} }
    """
    import pickle

    import httpx

    body = await request.json()
    target_url = body.get("url", "")
    method = body.get("method", "GET").upper()
    token = body.get("token", "")
    payload = body.get("body", None)
    do_login = body.get("login", False)
    params = body.get("params", {})

    if not target_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No url provided")
    if target_url != "LOGIN_ONLY":
        _require_allowed_xo_proxy_url(target_url)

    cookies_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "xo_cookies.pkl")
    cookies_path = os.path.normpath(cookies_path)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Load saved cookies if they exist
            saved_cookies = {}
            if os.path.exists(cookies_path):
                try:
                    with open(cookies_path, "rb") as f:
                        saved_cookies = pickle.load(f)
                except Exception:
                    saved_cookies = {}

            # If login requested, hit the full app URL with ALL params to get session cookies
            login_info = None
            if do_login and token:
                hmac_val = params.get("hmac", "")
                session_val = params.get("session", "")
                timestamp_val = params.get("timestamp", "")
                login_url = (
                    f"https://gallery.xopify.com/app"
                    f"?embedded=1"
                    f"&hmac={hmac_val}"
                    f"&host=YWRtaW4uc2hvcGlmeS5jb20vc3RvcmUvb2xzLW9ubGluZQ"
                    f"&id_token={token}"
                    f"&locale=en-US"
                    f"&session={session_val}"
                    f"&shop=ols-online.myshopify.com"
                    f"&timestamp={timestamp_val}"
                )
                login_resp = await client.get(login_url)
                saved_cookies = dict(client.cookies)
                with open(cookies_path, "wb") as f:
                    pickle.dump(saved_cookies, f)
                login_info = {
                    "login_status": login_resp.status_code,
                    "cookies_saved": len(saved_cookies),
                }
                # If only login requested, return
                if target_url == "LOGIN_ONLY":
                    return {"status": "ok", **login_info}

            # Make the actual API request with cookies
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if payload is not None:
                headers["Content-Type"] = "application/json"

            if method == "GET":
                resp = await client.get(target_url, headers=headers, cookies=saved_cookies)
            elif method == "POST":
                resp = await client.post(target_url, headers=headers, cookies=saved_cookies, json=payload)
            elif method == "PUT":
                resp = await client.put(target_url, headers=headers, cookies=saved_cookies, json=payload)
            elif method == "PATCH":
                resp = await client.patch(target_url, headers=headers, cookies=saved_cookies, json=payload)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported method: {method}",
                )

            # Update saved cookies
            new_cookies = dict(resp.cookies)
            if new_cookies:
                saved_cookies.update(new_cookies)
                with open(cookies_path, "wb") as f:
                    pickle.dump(saved_cookies, f)

        try:
            resp_json = resp.json()
        except Exception:
            resp_json = None

        result = {
            "status": "ok",
            "http_status": resp.status_code,
            "body": resp_json,
            "text": resp.text[:5000] if resp_json is None else None,
        }
        if login_info:
            result["login_info"] = login_info
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise_route_error(logger, "XO proxy", e)


# reload-trigger 1775322499
# reload-trigger 1775322842
# reload 1775323215
