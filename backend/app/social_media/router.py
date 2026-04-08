# ============================================================
# router.py — FastAPI Router (Async Job-Based)
# Social Media Asset Generation Module
# ============================================================

import logging
import traceback
import json
import os
import uuid
import tempfile
import asyncio
from fastapi import APIRouter, File, UploadFile, Form, Path, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse, Response
import httpx
from typing import Optional, List
from app.social_media.service import generate_all_assets, JOBS, update_job_status, get_s3_history, delete_s3_batch, delete_s3_item

logger = logging.getLogger("social_media.router")

router = APIRouter()

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp"
}

# ─────────────────────────────────────────────────────────────
# POST /social-media/generate  (non-blocking — returns job_id)
# ─────────────────────────────────────────────────────────────
@router.post("/social-media/generate")
async def generate_social_media_assets(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Manuscript file (PDF or DOCX)"),
    book_title: str = Form(..., description="Title of the book"),
    author_name: str = Form(..., description="Author's full name"),
    generate_images: bool = Form(True, description="Whether to generate images"),
    generate_videos: bool = Form(True, description="Whether to generate videos"),
    cover_image: Optional[UploadFile] = File(
        None,
        description="Book cover image (JPG/PNG) — optional. If not provided, video outro shows logo only."
    ),
    num_cover: int = Form(12, description="Number of Book Cover poster variants"),
    num_available: int = Form(2, description="Number of Available Now posts"),
    num_soon: int = Form(2, description="Number of Coming Soon posts"),
    num_others: int = Form(4, description="Number of Narrative Beat/Quote posts"),
    num_videos: int = Form(2, description="Number of video assets (Max 5)"),
):
    """
    Kick off async social media asset generation.
    Returns a job_id immediately; poll GET /social-media/job/{job_id} for status.
    """
    logger.info("=== POST /social-media/generate (async) ===")
    logger.info(f"Book: '{book_title}' by {author_name}")

    # ── Validate manuscript (PDF or DOCX) ────────────────
    ext = file.filename.lower()
    if not (ext.endswith(".pdf") or ext.endswith(".docx")):
        return JSONResponse(status_code=400, content={"success": False, "message": "Only PDF and DOCX files are accepted for the manuscript."})

    book_title  = book_title.strip()
    author_name = author_name.strip()
    if not book_title:
        return JSONResponse(status_code=400, content={"success": False, "message": "Book title is required."})
    if not author_name:
        return JSONResponse(status_code=400, content={"success": False, "message": "Author name is required."})

    try:
        # Read files upfront (before async background task)
        manuscript_bytes = await file.read()
        if len(manuscript_bytes) == 0:
            return JSONResponse(status_code=400, content={"success": False, "message": "The manuscript file is empty."})

        cover_bytes: Optional[bytes] = None
        cover_filename = "cover.jpg"
        if cover_image is not None:
            content_type = cover_image.content_type or ""
            if content_type not in ALLOWED_IMAGE_TYPES and not any(
                cover_image.filename.lower().endswith(ext)
                for ext in [".jpg", ".jpeg", ".png", ".webp"]
            ):
                return JSONResponse(status_code=400, content={"success": False, "message": f"Cover image must be JPG, PNG, or WebP."})
            cover_bytes    = await cover_image.read()
            cover_filename = cover_image.filename or "cover.jpg"

        # ── Create job ─────────────────────────────────
        job_id = str(uuid.uuid4())
        update_job_status(job_id, "pending", "Queued")

        # ── Run pipeline in background ───────────────────────
        async def _run_pipeline():
            try:
                update_job_status(job_id, "running", "Processing")
                result = await generate_all_assets(
                    manuscript_bytes=manuscript_bytes,
                    book_title=book_title,
                    author_name=author_name,
                    cover_bytes=cover_bytes,
                    cover_filename=cover_filename,
                    job_id=job_id,
                    book_subtitle="",      # UI update pending
                    book_positioning="",    # UI update pending
                    generate_images=(num_cover + num_available + num_soon + num_others) > 0,
                    generate_videos=num_videos > 0,
                    num_cover=num_cover,
                    num_available=num_available,
                    num_soon=num_soon,
                    num_others=num_others,
                    num_videos=num_videos,
                    manuscript_filename=file.filename
                )
                update_job_status(job_id, "completed", "Done", result=result)
                logger.info(f"Job {job_id} completed successfully")
            except Exception as e:
                error_msg = str(e)
                if "402" in error_msg or "credits" in error_msg.lower():
                    error_msg = "More Credits needed."
                update_job_status(job_id, "failed", "Error", error=error_msg)
                logger.error(f"Job {job_id} failed: {error_msg}")
                logger.error(traceback.format_exc())

        background_tasks.add_task(_run_pipeline)

        return JSONResponse(status_code=202, content={
            "success": True,
            "job_id": job_id,
            "message": "Generation started. Poll /social-media/job/{job_id} for status.",
        })

    except Exception as e:
        logger.error("Unexpected error in /social-media/generate")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "message": f"Server error: {str(e)}"})


@router.get("/social-media/job/{job_id}")
async def get_job_status(job_id: str = Path(..., description="Job ID from /social-media/generate")):
    """Poll the status of a video generation job."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"success": False, "message": "Job not found"})

    response = {
        "success": True,
        "job_id": job_id,
        "status": job["status"],   # pending | running | completed | failed
        "step": job["step"],
    }
    if job["status"] == "completed" and job["result"]:
        response["result"] = job["result"]
    if job["status"] == "failed" and job["error"]:
        response["error"] = job["error"]

    return response


# ─────────────────────────────────────────────────────────────
# GET /social-media/assets  (session history)
# ─────────────────────────────────────────────────────────────
@router.get("/social-media/history")
async def get_social_media_history():
    """
    Universal session history endpoint. 
    Lists all generation manifests from S3.
    """
    try:
        batches = await get_s3_history()
        return {"success": True, "batches": batches}
    except Exception as e:
        logger.error(f"Failed to fetch S3 history: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.get("/social-media/assets")
async def get_social_media_assets_legacy():
    """Alias for history endpoint."""
    return await get_social_media_history()


# ─────────────────────────────────────────────────────────────
# POST /social-media/delete-asset/{batch_id}
# ─────────────────────────────────────────────────────────────
@router.post("/social-media/delete-asset/{batch_id}")
async def delete_social_media_batch(batch_id: str = Path(...)):
    """Deletes a generation batch from S3 history."""
    try:
        success = await delete_s3_batch(batch_id)
        if success:
            return {"success": True, "message": f"Batch {batch_id} deleted from history"}
        else:
            return JSONResponse(status_code=404, content={"success": False, "message": "Batch not found in cloud history"})
    except Exception as e:
        logger.error(f"Failed to delete batch {batch_id}: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ─────────────────────────────────────────────────────────────
# POST /social-media/delete-item
# ─────────────────────────────────────────────────────────────
@router.post("/social-media/delete-item")
async def delete_social_media_item(
    batch_id: str = Form(...),
    asset_url: str = Form(...),
):
    """Deletes a single asset from an S3 batch manifest."""
    try:
        success = await delete_s3_item(batch_id, asset_url)
        if success:
            return {"success": True, "message": "Asset deleted from history"}
        else:
            return JSONResponse(status_code=404, content={"success": False, "message": "Asset or Batch not found in cloud history"})
    except Exception as e:
        logger.error(f"Failed to delete item {asset_url} from batch {batch_id}: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

# ─────────────────────────────────────────────────────────────
# GET /social-media/download (Proxy to bypass CORS)
# ─────────────────────────────────────────────────────────────
@router.get("/social-media/download")
async def proxy_download_asset(
    url: str = Query(..., description="The S3 or external URL to download"),
    filename: str = Query(None, description="Optional filename for the download")
):
    """
    Backend proxy for asset downloads to bypass CORS restrictions.
    Fetches the asset and streams it with proper Content-Type.
    """
    logger.info(f"--- Proxy Download Request: {url} ---")
    if filename:
        logger.info(f"Target filename: {filename}")

    if not url.startswith("http"):
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid URL"})

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=60.0)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch asset for download: {response.status_code} | URL: {url}")
            return JSONResponse(status_code=response.status_code, content={"success": False, "message": f"Source failed: {response.status_code}"})

        content_type = response.headers.get("Content-Type", "application/octet-stream")
        body = response.content  # all bytes in memory — guaranteed complete
        logger.info(f"Source Status: {response.status_code} | Content-Type: {content_type} | Bytes fetched: {len(body)}")

        headers = {}
        if filename:
            safe_filename = filename.replace('"', '').replace("'", "")
            headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'

        return Response(content=body, media_type=content_type, headers=headers)

    except Exception as e:
        logger.error(f"Download proxy failed for {url}: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to proxy download"})
