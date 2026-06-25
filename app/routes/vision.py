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
from base64 import b64decode
from binascii import Error as Base64Error
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api_errors import APIError, build_error_payload, service_result_or_raise
from app.db.database import SessionLocal, get_db
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
VISION_XO_RUNBOOK = "scripts/vision_xo_local_workflow.md"
logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEBUG_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
DEBUG_UPLOAD_ALLOWED_SUFFIXES = {".csv", ".json", ".txt", ".xlsx"}


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


def _safe_data_file(
    filename: str,
    *,
    allowed_suffixes: set[str] | None = None,
) -> Path:
    """Resolve a filename inside data/ without allowing traversal."""
    if not isinstance(filename, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    candidate_name = Path(filename).name
    if not candidate_name or candidate_name != filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    path = (DATA_DIR / candidate_name).resolve()
    if DATA_DIR.resolve() not in path.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    if allowed_suffixes is not None and path.suffix.lower() not in allowed_suffixes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )

    return path


def _write_private_bytes(path: Path, content: bytes) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as file_obj:
        file_obj.write(content)


def _write_private_json(path: Path, payload: dict) -> None:
    _write_private_bytes(path, json.dumps(payload, sort_keys=True).encode("utf-8"))


def _read_private_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    return payload if isinstance(payload, dict) else {}


@router.get("/images")
def list_shopify_images(limit: int = 50):
    """
    Pull image URLs from Shopify Files API.

    Returns image URLs, filenames, and existing alt text.
    """
    images = pull_image_urls(limit=limit)
    return {
        "status": "success",
        "count": len(images),
        "images": images,
    }


@router.get("/images/theme")
def list_theme_images(filter_prefix: str = "photo", limit: int = 250):
    """
    Pull image URLs from Shopify Theme Assets.

    XO Gallery stores estate sale photos as theme assets.
    filter_prefix: filter filenames starting with this (default: "photo")
    """
    images = pull_theme_assets(filter_prefix=filter_prefix, limit=limit)
    return {
        "status": "success",
        "count": len(images),
        "images": images,
    }


@router.get("/images/page/{page_handle}")
def list_page_images(page_handle: str):
    """
    Pull image URLs embedded in a specific Shopify page.

    Useful for finding XO Gallery images on a particular estate sale page.
    """
    images = pull_gallery_images_from_page(page_handle)
    return {
        "status": "success",
        "page_handle": page_handle,
        "count": len(images),
        "images": images,
    }


@router.get("/themes")
def list_themes():
    """
    List all Shopify themes.

    XO Gallery stores images under an older theme (e.g., theme 7)
    while the storefront uses the active/main theme.
    """
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


@router.get("/images/xo-gallery/local")
def list_local_xo_gallery_images(gallery_id: str = None, limit: int = 100):
    """
    List XO Gallery images from the locally saved JSON file.

    Use gallery_id to filter to a specific gallery.
    Returns image URLs constructed from base_url + filename.
    """
    if not os.path.exists(XO_GALLERY_DATA_FILE):
        raise APIError(
            status_code=404,
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
    if source == "xo-gallery":
        images = pull_xo_gallery_assets(
            filter_prefix="photo", limit=limit
        )
    elif source == "local":
        if not os.path.exists(XO_GALLERY_DATA_FILE):
            raise APIError(
                status_code=404,
                detail=(
                    "No local XO Gallery data. Import it first via "
                    "POST /api/vision/images/xo-gallery/import."
                ),
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
    elif source == "page":
        if not page_handle:
            raise APIError(
                status_code=400,
                detail="page_handle is required when source='page'.",
            )
        images = pull_gallery_images_from_page(page_handle)
    elif source == "files":
        images = pull_image_urls(limit=limit)
    else:
        raise APIError(
            status_code=400,
            detail=f"Unsupported image source '{source}'.",
        )

    if not images:
        return {
            "status": "warning",
            "detail": "No images found to analyze.",
        }

    return analyze_gallery_images(
        db=db,
        image_urls=images,
        gallery_name=gallery_name,
        batch_size=limit,
    )


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
    return service_result_or_raise(
        bulk_analyze_with_budget(
            db=db,
            budget_dollars=budget,
        )
    )


# Global status tracker for background alt text push
_alt_push_status = {"running": False, "result": None}


def _run_alt_push_background(force: bool):
    """Run alt text push in a background thread with its own DB session."""
    global _alt_push_status
    _alt_push_status = {"running": True, "result": None, "progress": {}}

    def progress_callback(stats):
        _alt_push_status["progress"] = stats

    db = SessionLocal()
    try:
        result = bulk_push_alt_text(db=db, force=force, progress_callback=progress_callback)
        _alt_push_status = {"running": False, "result": result}
    except Exception as exc:
        _alt_push_status = {
            "running": False,
            "result": build_error_payload(
                status_code=500,
                detail=str(exc),
                code="internal_server_error",
            ),
        }
    finally:
        db.close()


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
    except Exception as exc:
        _fix_empty_status = {
            "running": False,
            "result": build_error_payload(
                status_code=500,
                detail=str(exc),
                code="internal_server_error",
            ),
        }


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
    return compare_alt_text(db=db, sample_size=sample_size)


@router.get("/results")
def get_results(db: Session = Depends(get_db)):
    """Get a summary of all image analysis results."""
    summary = get_analysis_summary(db)
    return {"status": "success", **summary}


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

    from app.services.shopify_service import _get_access_token

    token = _get_access_token()

    page = _fetch_shopify_file_ids(limit=1)
    if not page["files"]:
        raise APIError(
            status_code=404,
            detail="No Shopify files found for mutation test.",
        )

    file_info = page["files"][0]
    file_id = file_info["id"]
    filename = file_info["filename"]
    current_alt = file_info["current_alt"]

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
        "token_configured": bool(token),
        "file_id": file_id,
        "filename": filename,
        "current_alt": current_alt,
        "test_alt_text": test_alt,
        "http_status": resp.status_code,
        "raw_response": resp.json(),
    }


@router.get("/debug/alt-text-audit")
def debug_alt_text_audit(
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """
    Scan all Shopify files and count how many have empty vs non-empty alt text.
    Returns counts and a sample of files with empty alt text.
    """
    from app.services.vision_service import _fetch_shopify_file_ids

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
    csv_content = export_analysis_csv(db, gallery_name=gallery_name)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=image_analysis.csv"
        },
    )


@router.get("/gallery-structure")
def get_gallery_structure():
    """Retired insecure helper endpoint."""
    raise APIError(
        status_code=410,
        detail=(
            "This browser helper endpoint has been retired. "
            f"Use the local operator workflow in {VISION_XO_RUNBOOK}."
        ),
    )


@router.post("/save-file")
async def save_file(
    request: Request,
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """Save an uploaded base64 file to the private data directory."""
    body = await request.json()
    filename = body.get("filename", "output.xlsx")
    b64data = body.get("data", "")
    if not b64data:
        raise APIError(status_code=400, detail="No data provided")

    save_path = _safe_data_file(
        filename,
        allowed_suffixes=DEBUG_UPLOAD_ALLOWED_SUFFIXES,
    )
    try:
        file_bytes = b64decode(b64data, validate=True)
    except (Base64Error, ValueError) as exc:
        raise APIError(status_code=400, detail="Invalid base64 data") from exc

    if len(file_bytes) > DEBUG_UPLOAD_MAX_BYTES:
        raise APIError(status_code=413, detail="Uploaded file is too large")

    _write_private_bytes(save_path, file_bytes)
    return {"status": "ok", "path": str(save_path), "size": len(file_bytes)}


@router.get("/store-token")
def store_token(
    t: str = "",
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """Store an operator-provided session token in a private local file."""
    if not t:
        raise APIError(status_code=400, detail="No token")

    token_path = _safe_data_file("xo_session_token.txt")
    _write_private_bytes(token_path, t.encode("utf-8"))

    from fastapi.responses import Response

    pixel = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    return Response(content=pixel, media_type="image/png")


@router.get("/get-token")
def get_stored_token(
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """Return token status metadata without exposing the raw token."""
    import base64 as base64_mod
    import time

    token_path = _safe_data_file("xo_session_token.txt")
    if not os.path.exists(token_path):
        raise APIError(status_code=404, detail="No token stored")

    with open(token_path, "r", encoding="utf-8") as file_obj:
        token = file_obj.read().strip()

    parts = token.split(".")
    if len(parts) == 3:
        padded = parts[1] + "=="
        payload = base64_mod.b64decode(padded)
        payload_json = json.loads(payload)
        exp = payload_json.get("exp", 0)
        now = int(time.time())
        return {
            "status": "ok",
            "present": True,
            "exp": exp,
            "now": now,
            "expired": now > exp,
        }

    return {"status": "ok", "present": True, "expired": None}


@router.post("/xo-proxy")
async def xo_proxy(
    request: Request,
    _debug_tools: None = Depends(require_vision_debug_tools_enabled),
):
    """
    Debug-only server-side proxy for XO Gallery API calls.

    Body: {
        "url": "...",
        "method": "GET" | "POST" | "PUT" | "PATCH",
        "token": "...",
        "body": {...},
        "login": true | false,
        "params": {"hmac": "...", "session": "...", "timestamp": "..."}
    }
    """
    import httpx

    body = await request.json()
    target_url = body.get("url", "")
    method = body.get("method", "GET").upper()
    token = body.get("token", "")
    payload = body.get("body")
    do_login = body.get("login", False)
    params = body.get("params", {})

    if not target_url:
        raise APIError(status_code=400, detail="No url provided")
    if target_url != "LOGIN_ONLY":
        _require_allowed_xo_proxy_url(target_url)

    cookies_path = _safe_data_file("xo_cookies.json")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        saved_cookies = {}
        if os.path.exists(cookies_path):
            try:
                saved_cookies = _read_private_json(cookies_path)
            except Exception:
                saved_cookies = {}

        login_info = None
        if do_login and token:
            hmac_val = params.get("hmac", "")
            session_val = params.get("session", "")
            timestamp_val = params.get("timestamp", "")
            login_url = (
                "https://gallery.xopify.com/app"
                f"?embedded=1&hmac={hmac_val}"
                "&host=YWRtaW4uc2hvcGlmeS5jb20vc3RvcmUvb2xzLW9ubGluZQ"
                f"&id_token={token}"
                f"&locale=en-US&session={session_val}"
                "&shop=ols-online.myshopify.com"
                f"&timestamp={timestamp_val}"
            )
            login_resp = await client.get(login_url)
            saved_cookies = dict(client.cookies)
            _write_private_json(cookies_path, saved_cookies)
            login_info = {
                "login_status": login_resp.status_code,
                "cookies_saved": len(saved_cookies),
            }
            if target_url == "LOGIN_ONLY":
                return {"status": "ok", **login_info}

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if payload is not None:
            headers["Content-Type"] = "application/json"

        if method == "GET":
            response = await client.get(
                target_url,
                headers=headers,
                cookies=saved_cookies,
            )
        elif method == "POST":
            response = await client.post(
                target_url,
                headers=headers,
                cookies=saved_cookies,
                json=payload,
            )
        elif method == "PUT":
            response = await client.put(
                target_url,
                headers=headers,
                cookies=saved_cookies,
                json=payload,
            )
        elif method == "PATCH":
            response = await client.patch(
                target_url,
                headers=headers,
                cookies=saved_cookies,
                json=payload,
            )
        else:
            raise APIError(status_code=400, detail=f"Unsupported method: {method}")

        new_cookies = dict(response.cookies)
        if new_cookies:
            saved_cookies.update(new_cookies)
            _write_private_json(cookies_path, saved_cookies)

    try:
        response_json = response.json()
    except Exception:
        response_json = None

    result = {
        "status": "ok",
        "http_status": response.status_code,
        "body": response_json,
        "text": response.text[:5000] if response_json is None else None,
    }
    if login_info:
        result["login_info"] = login_info
    return result


# reload-trigger 1775322499
# reload-trigger 1775322842
# reload 1775323215
