# ============================================================
# service.py — Orchestration Pipeline
# Social Media Asset Generation Module
# ============================================================
#
# Pipeline:
#   PDF bytes + Cover image bytes
#     → extract manuscript text
#     → upload cover to FAL storage (get public URL)
#     → generate post ideas & video concepts (OpenRouter)
#     → build image prompts (scene-based, cover as hero product)
#     → generate 30 images (FAL flux-pro image-to-image, cover as ref)
#     → generate 4 videos (FAL minimax-video)
#     → generate captions for 4 platforms (OpenRouter)
#     → return assembled assets
#
# ============================================================

import asyncio
import logging
import traceback
import json
import os
import uuid
from datetime import datetime
from typing import Optional
from app.social_media.manuscript_parser import extract_text
from app.social_media.generators import (
    detect_genre_async,
    generate_post_ideas,
    generate_video_prompt_pipeline,
    generate_single_image,
    generate_video,
    generate_caption,
    upload_cover_image,
    process_video_outro,
    extract_book_metadata_async,
    generate_image_concepts_pipeline,
)
from app.social_media.prompts import (
    # Prompts now handled internally by generators
    IMAGE_EXTRACTION_PROMPT, 
    IMAGE_RANKING_PROMPT,
    build_flux_image_prompt
)
from app.social_media.s3_client import (
    upload_video, 
    upload_image, 
    upload_manifest, 
    list_manifests, 
    get_s3_object_json, 
    delete_manifest
)
import shutil
from pathlib import Path
import aiohttp

logger = logging.getLogger("social_media.service")

# ────────────────────────────────────────────────────────────
# Job Memory Store (Stateless)
# ────────────────────────────────────────────────────────────
JOBS: dict = {}

def update_job_status(job_id: str, status: str, step: str, result: dict = None, error: str = None):
    """Synchronized update for the in-memory job store."""
    if not job_id: return
    
    if job_id not in JOBS:
        JOBS[job_id] = {}
        
    JOBS[job_id]["status"] = status
    JOBS[job_id]["step"] = step
    if result: JOBS[job_id]["result"] = result
    if error:  JOBS[job_id]["error"] = error

# ────────────────────────────────────────────────────────────
# Image distribution :
#   18 → book cover poster variants  (portrait 1080×1350)
#    3 → Available Now               (square  1080×1080)
#    3 → Coming Soon                 (square  1080×1080)
#    6 → quotes/concepts             (portrait 1080×1350)
# ────────────────────────────────────────────────────────────

# Standard asset counts
BOOK_COVER_COUNT    = 1
AVAILABLE_NOW_COUNT = 0
COMING_SOON_COUNT   = 1
QUOTE_COUNT         = 1

PORTRAIT_SIZE = (1080, 1920)
SQUARE_SIZE   = (1080, 1080)

# 18 different scene/mood variations for book cover posters
# 18 different scene/mood variations (DEPRECATED: Now dynamically extracted)
# BOOK_COVER_VARIATIONS = [...] 

# Taglines for Available Now and Coming Soon images
AVAILABLE_NOW_TAGLINES = [
    "Order Your Copy Today",
    "Now Available Everywhere",
    "Get Your Copy Now",
]
COMING_SOON_TAGLINES = [
    "Coming Soon — Pre-Order Now",
    "Your Next Breakthrough Is Coming",
    "Be First in Line",
]


async def generate_all_assets(
    manuscript_bytes: bytes,
    book_title: str,
    author_name: str,
    cover_bytes: Optional[bytes] = None,
    cover_filename: str = "cover.jpg",
    job_id: Optional[str] = None,
    book_subtitle: str = "",
    book_positioning: str = "",
    generate_images: bool = True,
    generate_videos: bool = True,
    num_cover: int = 12,
    num_available: int = 2,
    num_soon: int = 2,
    num_others: int = 4,
    num_videos: int = 2,
    manuscript_filename: str = ""
) -> dict:
    """
    Full orchestration pipeline.

    Args:
        manuscript_bytes: Raw bytes of the uploaded manuscript (PDF or DOCX)
        book_title:       Title of the book
        author_name:      Author's full name
        cover_bytes:      Raw bytes of the uploaded book cover image (optional)
        cover_filename:   Original filename of the cover image (for MIME detection)
        job_id:           Optional job ID to update progress in JOBS store
        manuscript_filename: Original filename of the manuscript (for format detection)

    Returns a dict with:
      images:     list[dict] — {url, category, format, status}
      videos:     list[dict] — {url, concept, status}
      captions:   dict       — {instagram: [...], facebook: [...], linkedin: [...], x: []}
      post_ideas: list[str]
      stats:      dict
    """

    def _update_job(status: str, step: str):
        update_job_status(job_id, status, step)

    logger.info(f"=== Asset generation pipeline start: '{book_title}' by {author_name} ===")
    
    # Generate unique job_id if not present
    if not job_id:
        job_id = str(uuid.uuid4())[:8]

    # Create temp directory for S3 preparation
    temp_dir = Path(f"/tmp/social_media/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def _download_file(url: str, local_path: Path):
        # Increased timeout to 60s for large files/slow connections
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(local_path, "wb") as f:
                            f.write(content)
                        return True
                    else:
                        logger.error(f"Download failed with status {response.status} for {url}")
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
        return False

    _update_job("running", "Extracting manuscript text")
    logger.info("Step 1: Extracting manuscript text")
    manuscript_text = extract_text(manuscript_bytes, filename=manuscript_filename)
    logger.info(f"Extracted {len(manuscript_text)} characters from manuscript")

    # ── Step 2: Upload cover image to FAL storage ─────────────
    _update_job("running", "Uploading book cover to FAL")
    cover_image_url: Optional[str] = None
    if cover_bytes:
        logger.info("Step 2: Uploading book cover to FAL storage")
        try:
            cover_image_url = await upload_cover_image(cover_bytes, filename=cover_filename)
            logger.info(f"Cover URL: {cover_image_url}")
        except Exception as e:
            logger.error(f"CRITICAL: Cover upload failed: {e}")
            logger.warning("Skipping image generation to preserve credits.")
            cover_image_url = None
    else:
        logger.warning("Step 2: No cover image supplied — image generation will be skipped to save credits.")

    # ── Step 3: Generate post ideas + video concepts ──────────
    _update_job("running", "Detecting book genre and ideas")
    logger.info("Step 3: Detecting genre and generating concepts")
    
    # Auto-detect genre and metadata (subtitle/positioning)
    genre_task    = detect_genre_async(manuscript_text)
    metadata_task = extract_book_metadata_async(manuscript_text)
    
    genre_result, metadata = await asyncio.gather(genre_task, metadata_task)
    
    # - [x] Update `service.py` orchestration to extract data once and reuse it <!-- id: 3 -->
    # - [x] Verify pipeline with a test run <!-- id: 4 -->
    if "primary_genre" not in metadata or not metadata["primary_genre"]:
        metadata["primary_genre"] = genre_result

    # ── BRANDING PRESERVATION ─────────────────────────────────
    # Ensure metadata ALWAYS has the user-provided title/author as a base fallback
    # But ONLY overwrite user titles if extraction found something extremely specific (not 'Unknown')
    if "book_title" not in metadata or not metadata["book_title"] or metadata["book_title"].lower() == "unknown":
        metadata["book_title"] = book_title
    if "author_name" not in metadata or not metadata["author_name"] or metadata["author_name"].lower() == "unknown":
        metadata["author_name"] = author_name

    genre              = metadata.get("primary_genre", "NONFICTION")
    book_subtitle      = metadata.get("book_subtitle", "")
    positioning_label  = metadata.get("positioning_label", "MASTERY")
    positioning_desc   = metadata.get("positioning_desc", "")
    banned_visuals     = metadata.get("genre_specific_banned_visuals", "None specified.")
    
    # Sync global variables with (possibly refined) metadata
    book_title = metadata["book_title"]
    author_name = metadata["author_name"]


    # Sync global variables with (possibly refined) metadata
    book_title = metadata["book_title"]
    author_name = metadata["author_name"]
    
    logger.info(f"★★★ [GENRE DETECTED]: {genre} ★★★")
    logger.info(f"★★★ [LABEL]: {positioning_label} ★★★")
    logger.info(f"★★★ [DESC]: {positioning_desc} ★★★")
    
    # ── Asset Allocation ───────────────────────────────────────
    # Use explicit counts from the frontend
    total_posts = num_cover + num_available + num_soon + num_others
    
    # Only force a cover if EVERYTHING is zero (fail-safe)
    if total_posts == 0 and generate_images and not generate_videos:
        num_cover = 1
        total_posts = 1
    
    categories = (["book_cover"] * num_cover + 
                  ["available_now"] * num_available + 
                  ["coming_soon"] * num_soon + 
                  ["quote"] * num_others)
    
    # Map strengths based on category
    # Keep ALL strengths at 0.10 — lowest value that still allows scene creativity
    # while preserving the uploaded book cover as close to pixel-perfect as possible
    strengths = []
    for c in categories:
        strengths.append(0.10)  # Uniform low strength: preserve book cover across ALL categories

    logger.info(f"Allocation: {num_cover} Cover, {num_available} Avail, {num_soon} Soon, {num_others} Others")

    # Pass the entire metadata (The Brain) to downstream generators
    if total_posts > 50:
        post_ideas     = await generate_post_ideas(metadata, count=total_posts)
    else:
        post_ideas     = await generate_post_ideas(metadata, count=total_posts)
    logger.info(f"Got {len(post_ideas)} post ideas")

    # Pad to required lengths
    while len(post_ideas) < total_posts: post_ideas.append(f"Key insight from {book_title}")

    image_concepts = []
    if generate_images and cover_image_url:
        # ───────────────── Step 3.5: Generate Image Concepts (New Pipeline) ─────────
        _update_job("running", "Generating image concepts from manuscript")
        logger.info("Step 3.5: Running image concept pipeline")

        # Use the new pipeline (manuscript + metadata)
        image_concepts = await generate_image_concepts_pipeline(
            manuscript_text=manuscript_text,
            metadata=metadata,
            num_concepts=15  # Generate 15 concepts
        )
        logger.info(f"Generated {len(image_concepts)} image concepts")
    else:
        logger.warning("Skipping image concept generation: generate_images=False or cover_image_url missing")

    # ───────────────── Step 4: Build Image Prompts ────────────────────────────
    _update_job("running", "Building image prompts")
    logger.info("Step 4: Building image prompt list")

    # Define category distribution
    categories = (
        ["book_cover"] * num_cover + 
        ["available_now"] * num_available + 
        ["coming_soon"] * num_soon + 
        ["quote"] * num_others
    )

    image_tasks = []

    for idx, category in enumerate(categories):
        # Cycle through concepts if more images than concepts (Harden against empty lists)
        if not image_concepts:
            logger.warning("[SERVICE] No image concepts found! Using emergency fallback.")
            concept = {
                "subject": "A minimalistic architectural space",
                "emotion": "contemplative",
                "placement": "soft lighting",
                "visual_vibe": "premium cinematic"
            }
        else:
            concept = image_concepts[idx % len(image_concepts)]
        
        # Build the exact payload that will be sent to FAL
        payload = build_flux_image_prompt(
            concept=concept,
            book_title=book_title,
            author_name=author_name,
            category=category,
            cover_image_url=cover_image_url
        )
        
        # Prepare task with pre-built payload
        image_tasks.append({
            "concept": concept,
            "category": category,
            "payload": payload
        })

    logger.info(f"Total image tasks: {len(image_tasks)}")

    # ───────────────── Step 5: Generate Images ────────────────────────────────
    images = []

    if generate_images and cover_image_url and len(image_tasks) > 0:
        _update_job("running", f"Generating {len(image_tasks)} images via Flux Pro")
        logger.info(f"Step 5: Generating {len(image_tasks)} images via Flux Pro")
        
        BATCH_SZ = 3  # Flux Pro handles 3 concurrent well
        for batch_start in range(0, len(image_tasks), BATCH_SZ):
            batch = image_tasks[batch_start:batch_start + BATCH_SZ]
            
            async def _gen_safe(task):
                try:
                    url = await generate_single_image(
                        payload=task["payload"]
                    )
                    return {
                        "url": url,
                        "category": task["category"],
                        "format": "portrait",
                        "status": "ok",
                        "tagline": task["concept"].get("tagline", ""),
                        "emotion": task["concept"].get("emotion", "")
                    }
                except Exception as e:
                    logger.error(f"Image generation failed: {e}")
                    return {
                        "url": "",
                        "category": task["category"],
                        "format": "portrait",
                        "status": "failed",
                        "error": str(e)
                    }
            
            batch_results = await asyncio.gather(*[_gen_safe(t) for t in batch])
            
            # ── Upload images to S3 with retry ──
            for b_idx, res in enumerate(batch_results):
                if res["status"] == "ok" and res["url"]:
                    global_image_idx = batch_start + b_idx
                    local_img_path = temp_dir / f"image_{global_image_idx}.png"
                    fal_url = res["url"]
                    
                    # Retry download up to 3 times before giving up
                    downloaded = False
                    for attempt in range(3):
                        if await _download_file(fal_url, local_img_path):
                            downloaded = True
                            break
                        logger.warning(f"Download attempt {attempt+1}/3 failed for image {global_image_idx}")
                        await asyncio.sleep(2)
                    
                    if downloaded:
                        s3_url = upload_image(local_img_path, job_id, res["category"], global_image_idx)
                        if s3_url:
                            res["url"] = s3_url
                            logger.info(f"Image {global_image_idx} uploaded to S3: {s3_url}")
                        else:
                            logger.warning(f"S3 upload failed for image {global_image_idx}, keeping temporary FAL URL")
                    else:
                        logger.error(f"All download attempts failed for image {global_image_idx}. FAL URL may expire.")
            
            images.extend(batch_results)
            
            if batch_start + BATCH_SZ < len(image_tasks):
                await asyncio.sleep(1)  # Brief pause between batches
    else:
        logger.warning("Skipping image generation: cover_image_url missing or generate_images=False")
        # Create failed entries for UI feedback
        for task in image_tasks:
            images.append({
                "url": "",
                "category": task["category"],
                "format": "portrait",
                "status": "failed",
                "error": "Cover image missing or generation disabled"
            })

    ok_images = sum(1 for i in images if i["status"] == "ok")
    logger.info(f"Image generation done. OK: {ok_images}/{len(images)}")

    # ── Step 6: Generate promotional video (FAL) ─────────────
    videos = []
    if generate_videos and num_videos > 0:
        _update_job("running", f"Generating {num_videos} promotional videos (FAL)")
        logger.info(f"Step 6: Generating {num_videos} promotional videos")
        
        try:
            # ── NEW OPTIMIZED PIPELINE: Multi-stage prompt generation (Batch) ──
            _update_job("running", f"Running video prompt pipeline (Batch of {num_videos})")
            results = await generate_video_prompt_pipeline(manuscript_text, metadata, requested_video_count=num_videos)
            
            for idx, result in enumerate(results):
                try:
                    fal_prompt = result["fal_prompt"]
                    hook = result["hook"]
                    
                    # Append Book Title and Subtitle for complete branding (NO AUTHOR per user request)
                    subtitle = metadata.get("subtitle", "")
                    full_hook = book_title.upper()
                    if subtitle:
                        full_hook = f"{full_hook}: {subtitle.upper()}"
                    
                    # Prepend hook text to the branded title
                    final_hook = f"{hook}. {full_hook}"
                    
                    hook = final_hook

                    # ── Video Generation (Seedance) ──
                    _update_job("running", f"Dispatching video {idx+1} to FAL")
                    logger.info(f"Dispatching clean prompt to Seedance: {fal_prompt[:100]}...")
                    raw_path = await generate_video(fal_prompt, output_dir=str(temp_dir))

                    _update_job("running", f"Finalizing branding for video {idx+1}... Almost done.")
                    logger.info(f"Processing video {idx+1} outro with FFmpeg...")
                    video_abs_path = await process_video_outro(raw_path, cover_bytes=cover_bytes, hook_text=hook, output_dir=str(temp_dir))

                    # ── Upload to S3 ──
                    # We only upload the BRANDED version
                    s3_url = upload_video(Path(video_abs_path), job_id, idx)
                    if s3_url:
                        logger.info(f"Video {idx+1} uploaded to S3: {s3_url}")
                        final_url = s3_url
                    else:
                        # Fallback if S3 fails — but should be rare
                        final_url = video_abs_path 

                    # ── Save clean concept ──
                    clean_concept = {"hook": hook}
                    videos.append({"url": final_url, "concept": clean_concept, "status": "ok"})
                except Exception as e:
                    logger.warning(f"Video {idx + 1} item processing failed: {e}")
                    videos.append({"url": "", "concept": {"hook": result.get("hook", "")}, "status": "failed", "error": str(e)})
        except Exception as e:
            logger.error(f"Video prompt pipeline failed: {e}")
            _update_job("failed", f"Video pipeline failed: {str(e)}")
            # If the whole pipeline fails, add empty failed entries if num_videos > 0
            for i in range(num_videos):
                videos.append({"url": "", "concept": {}, "status": "failed", "error": f"Pipeline failure: {str(e)}"})
    else:
        logger.info("Skipping video generation as requested.")

    ok_videos = sum(1 for v in videos if v["status"] == "ok")
    logger.info(f"Video generation summary. OK: {ok_videos}/{len(videos)}")

    # ── Step 7: Generate Social Media Captions ───────────────
    # Uses the first post idea as the anchor for the generic platform captions
    _update_job("running", "Generating social media captions")
    logger.info("Step 7: Generating platform captions")
    
    captions = {"instagram": [], "facebook": [], "linkedin": [], "x": []}
    credits_exhausted = False
    try:
        from app.social_media.generators import generate_caption
        platforms = ["instagram", "facebook", "linkedin", "x"]
        
        # Use first post idea for the platform-wide captions
        concept_for_captions = post_ideas[0] if post_ideas else book_title
        
        caption_tasks = [generate_caption(p, concept_for_captions, book_title, author_name, metadata=metadata) for p in platforms]
        caption_results = await asyncio.gather(*caption_tasks, return_exceptions=True)
        
        for platform, result_item in zip(platforms, caption_results):
            if isinstance(result_item, Exception):
                err_str = str(result_item)
                if "402" in err_str or "credits" in err_str.lower():
                    credits_exhausted = True
                    logger.warning(f"OpenRouter credit limit hit during {platform} caption generation.")
                    captions[platform] = ["⚠️ Credits Low — Recharge OpenRouter to generate captions."]
                else:
                    logger.error(f"Caption generation failed for {platform}: {result_item}")
                    captions[platform] = []
            else:
                captions[platform] = [result_item]
    except Exception as e:
        err_str = str(e)
        if "402" in err_str or "credits" in err_str.lower():
            credits_exhausted = True
            logger.warning(f"OpenRouter credit limit hit during caption generation: {e}")
            for p in ["instagram", "facebook", "linkedin", "x"]:
                captions[p] = ["⚠️ Credits Low — Recharge OpenRouter to generate captions."]
        else:
            logger.error(f"Caption generation failed: {e}")
        
    # ── Step 8: Return assembled assets & Final Manifest ──
    _update_job("running", "Finalizing assets")
    
    # Upload manifest to S3
    manifest_data = {
        "id": job_id,
        "job_id": job_id,
        "book_title": book_title,
        "author_name": author_name,
        "timestamp": datetime.now().isoformat(),
        "images": [i for i in images if i["status"] == "ok" and i.get("url")],
        "videos": [v for v in videos if v["status"] == "ok" and v.get("url")],
        "captions": captions,
        "credits_exhausted": credits_exhausted,
    }
    manifest_url = upload_manifest(job_id, manifest_data)
    logger.info(f"Manifest uploaded to S3: {manifest_url}")

    # Cleanup temp directory
    shutil.rmtree(temp_dir, ignore_errors=True)

    result = {
        "id": job_id,
        "job_id": job_id,
        "book_title": book_title,
        "author_name": author_name,
        "timestamp": datetime.now().isoformat(),
        "manifest_url": manifest_url,
        "images": images,
        "videos": videos,
        "captions": captions,
        "post_ideas": post_ideas,
        "stats": {
            "image_count": len(images),
            "video_count": len(videos)
        }
    }
    return result

    return result

async def get_s3_history() -> list[dict]:
    """Retrieves all session manifests from S3 to build the global history."""
    import re
    from .s3_client import list_manifests, get_s3_object_json

    def normalize_url(url: str) -> str:
        if not url or "amazonaws.com" not in url:
            return url
        m = re.match(r"^https://([^.]+)\.s3\.([^.]+)\.amazonaws\.com/(.+)$", url)
        if m:
            bucket, region, key = m.group(1), m.group(2), m.group(3)
            return f"https://s3.{region}.amazonaws.com/{bucket}/{key}"
        return url

    def make_image_obj(item, index):
        if isinstance(item, dict):
            item["url"] = normalize_url(item.get("url", ""))
            item.setdefault("status", "ok")
            return item
        return {"url": normalize_url(item), "category": "book_cover", "status": "ok", "index": index}

    def make_video_obj(item):
        if isinstance(item, dict):
            item["url"] = normalize_url(item.get("url", ""))
            item.setdefault("status", "ok")
            return item
        return {"url": normalize_url(item), "status": "ok"}

    manifest_keys = list_manifests()
    logger.info(f"Found {len(manifest_keys)} manifests in S3")

    batches = []
    for key in manifest_keys:
        manifest = get_s3_object_json(key)
        if not manifest:
            continue
        if "id" not in manifest:
            manifest["id"] = manifest.get("job_id", key.split("/")[-1].replace(".json", ""))
        if "timestamp" not in manifest:
            manifest["timestamp"] = manifest.get("created_at", "")
        manifest["images"] = [make_image_obj(img, idx) for idx, img in enumerate(manifest.get("images", []))]
        manifest["videos"] = [make_video_obj(v) for v in manifest.get("videos", [])]
        batches.append(manifest)

    return batches

async def delete_s3_batch(job_id: str):
    """Deletes a batch from S3 history."""
    from app.social_media.s3_client import delete_manifest
    return delete_manifest(job_id)

async def delete_s3_item(job_id: str, asset_url: str):
    """Deletes a specific item from the S3 manifest."""
    from app.social_media.s3_client import get_s3_object_json, upload_manifest
    s3_key = f"manifest/{job_id}.json"
    manifest = get_s3_object_json(s3_key)
    if not manifest:
        return False

    orig_img = len(manifest.get("images", []))
    orig_vid = len(manifest.get("videos", []))

    manifest["images"] = [i for i in manifest.get("images", []) if i.get("url") != asset_url]
    manifest["videos"] = [v for v in manifest.get("videos", []) if v.get("url") != asset_url]

    if len(manifest["images"]) == orig_img and len(manifest["videos"]) == orig_vid:
        return False

    upload_manifest(job_id, manifest)
    return True
