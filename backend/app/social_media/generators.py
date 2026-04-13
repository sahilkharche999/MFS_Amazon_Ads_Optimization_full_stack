# ============================================================
# generators.py — AI Asset Generation (FAL + OpenRouter)
# Social Media Asset Generation Module
# ============================================================

import os
import logging
import asyncio
import json
import io
import httpx
import aiohttp
import uuid
import tempfile
import subprocess
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# Ensure environment is loaded in this module
load_dotenv()
if not os.getenv("FAL_KEY") and os.path.exists("../.env"):
    load_dotenv("../.env")

from app.social_media.prompts import (
    GUARDRAILS_SYSTEM_PROMPT,
    INSTAGRAM_CAPTION_PROMPT,
    LINKEDIN_CAPTION_PROMPT,
    FACEBOOK_CAPTION_PROMPT,
    X_CAPTION_PROMPT,
    VIDEO_HOOK_PROMPT,
    VIDEO_EXTRACTION_PROMPT,
    VIDEO_SCENARIO_PROMPT,
    VIDEO_RANKING_PROMPT,
    VIDEO_CINEMATIC_PROMPT,
    IMAGE_EXTRACTION_PROMPT,
    IMAGE_RANKING_PROMPT,
    FALLBACK_IMAGE_CONCEPTS,
    build_flux_image_prompt
)

logger = logging.getLogger("social_media.generators")

# ────────────────────────────────────────────────────────────
# OpenRouter client (for text/caption generation)
# ────────────────────────────────────────────────────────────
def get_openrouter_client() -> OpenAI:
    # Increased timeout to 300s to handle large prompts and slow responses
    return OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        timeout=300.0,
    )

def get_openai_client() -> OpenAI:
    # Standard OpenAI client for TTS and other native services
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
        timeout=60.0,
    )


# ────────────────────────────────────────────────────────────
# Upload cover image bytes → FAL storage URL
# ────────────────────────────────────────────────────────────
# Attempt to import fal_client at module level
try:
    import fal_client
    logger.info("FAL client successfully imported.")
except ImportError:
    fal_client = None
    logger.error("FAL client NOT found in this environment.")

# Local assets are now handled via temporary job workspaces

async def download_and_save_locally(url: str, ext: str = "webp", output_dir: Optional[str] = None) -> str:
    """
    Download a file from a URL and save it to a destination folder.
    Returns the absolute path to the saved file.
    """
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"
    dest_dir = output_dir or tempfile.gettempdir()
    os.makedirs(dest_dir, exist_ok=True)
    local_path = os.path.join(dest_dir, filename)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(response.content)
            return local_path
        else:
            logger.error(f"Failed to download asset from {url}: {response.status_code}")
            return url # Fallback to original URL if download fails

# ────────────────────────────────────────────────────────────
# Upload cover image bytes → FAL storage URL
# ────────────────────────────────────────────────────────────
async def upload_cover_image(cover_bytes: bytes, filename: str = "cover.jpg") -> str:
    """
    Upload the book cover image bytes to FAL's file storage and return
    a public URL usable as the image_url input for image-to-image generation.
    """
    if not fal_client:
        raise RuntimeError("fal-client is not installed. Please run 'pip install fal-client'.")

    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        raise RuntimeError("FAL_KEY environment variable is not set.")
    # Diagnostic: Show first 4 chars of key to verify identity
    logger.info(f"FAL Auth Check: Using key starting with '{fal_key[:4]}...'")
    os.environ["FAL_KEY"] = fal_key
    logger.info(f"Uploading cover image ({len(cover_bytes)} bytes) to FAL storage...")
    loop = asyncio.get_event_loop()

    def _upload():
        return fal_client.upload(cover_bytes, content_type="image/jpeg")

    url = await loop.run_in_executor(None, _upload)
    logger.info(f"Cover uploaded to FAL: {url[:60]}...")
    return url


# ────────────────────────────────────────────────────────────
# Image Generation via FAL.ai  (image-to-image w/ cover ref)
# ────────────────────────────────────────────────────────────
async def generate_image(
    prompt: str,
    width: int = 1080,
    height: int = 1350,
    cover_image_url: Optional[str] = None,
    strength: float = 0.30,
) -> str:
    """
    Generate a marketing poster image via FAL.ai.

    - If cover_image_url is provided: uses flux-pro image-to-image so the
      uploaded book cover acts as the reference product in the poster scene
      (strength 0.25-0.35 keeps the cover recognizable per Bryan's rule).
    - If no cover: falls back to standard text-to-image.

    Returns the URL of the generated image on FAL's CDN.
    """
    if not fal_client:
        raise RuntimeError(
            "fal-client is not installed. Please run 'pip install fal-client'."
        )

    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        raise RuntimeError("FAL_KEY environment variable is not set.")
    os.environ["FAL_KEY"] = fal_key

    loop = asyncio.get_event_loop()

    if not cover_image_url:
        raise ValueError("Image generation requires a cover_image_url for image-to-image processing.")

    logger.info(
        f"Generating img2img {width}x{height} strength={strength} | "
        f"prompt: {prompt[:80]}..."
    )

    def _run_img2img():
        # Correct literals for fal-ai/flux-2-pro/edit: 'portrait_4_3', 'square', etc.
        # portrait_4_5 is NOT supported; using portrait_4_3 as closest match.
        size_name = "portrait_4_3" if height > width else "square"
        
        return fal_client.run(
            "fal-ai/flux-2-pro/edit",
            arguments={
                "prompt": prompt,
                "image_urls": [cover_image_url],
                "strength": strength,
                "image_size": size_name,
                "num_images": 1,
                "output_format": "jpeg"
            },
        )

    result = await loop.run_in_executor(None, _run_img2img)

    images = result.get("images", [])
    if not images:
        raise RuntimeError(f"FAL returned no images. Response keys: {list(result.keys())}")

    url = images[0].get("url", "")
    logger.info(f"Image generated on FAL: {url[:80]}...")
    
    # Save locally
    local_url = await download_and_save_locally(url, ext="webp")
    logger.info(f"Saved locally to: {local_url}")
    return local_url




# ────────────────────────────────────────────────────────────
# Video Generation via FAL.ai
# ────────────────────────────────────────────────────────────
async def generate_video(prompt: str, output_dir: Optional[str] = None) -> str:
    """
    Generate a promotional video via ByteDance Seedance 1.5 Pro on FAL.ai.
    This model is chosen for better credit efficiency.
    Returns the video URL.
    """
    try:
        import fal_client
    except ImportError:
        raise RuntimeError("fal-client is not installed.")

    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        raise RuntimeError("FAL_KEY environment variable is not set.")

    os.environ["FAL_KEY"] = fal_key

    logger.info(f"Generating Seedance video | prompt: {prompt[:80]}...")

    loop = asyncio.get_event_loop()

    def _run_seedance():
        # Using ByteDance Seedance 1.5 Pro for credits optimization
        return fal_client.run(
            "fal-ai/bytedance/seedance/v1.5/pro/text-to-video",
            arguments={
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "resolution": "720p",
                "duration": 12, # 12 seconds
                "generate_audio": True
            },
        )

    result = await loop.run_in_executor(None, _run_seedance)

    # Seedance returns result["video"]["url"]
    video_url = result.get("video", {}).get("url", "")
    if not video_url:
        video_url = result.get("url", "")
    if not video_url and "video_url" in result:
        video_url = result["video_url"]

    if not video_url:
        raise RuntimeError(f"FAL returned no video URL. Response: {result}")

    logger.info(f"Video generated on FAL: {video_url[:80]}...")
    
    # Save locally
    local_path = await download_and_save_locally(video_url, ext="mp4", output_dir=output_dir)
    logger.info(f"Saved locally to: {local_path}")
    return local_path


# ────────────────────────────────────────────────────────────
# Video Outro Processing via FFmpeg
# ────────────────────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
LOGO_PATH = os.path.join(STATIC_DIR, "branding", "MFS logo.png")

async def process_video_outro(video_local_url: str, cover_bytes: Optional[bytes] = None, hook_text: str = "", output_dir: Optional[str] = None) -> str:
    """
    Append a branded outro to the FAL-generated video.
    Returns the absolute path to the processed video.
    """
    import subprocess
    import tempfile
    import shutil

    # ── Path Resolution (Improved for absolute paths) ────────────
    # If it's already an absolute path (like /tmp/...), use it directly.
    # Otherwise, resolve it relative to the app directory.
    if os.path.isabs(video_local_url):
        video_path = video_local_url
    else:
        app_dir = os.path.dirname(os.path.dirname(__file__))
        video_rel = video_local_url.lstrip("/")
        video_path = os.path.join(app_dir, video_rel)

    if not os.path.exists(video_path):
        logger.error(f"process_video_outro: input video not found: {video_path}")
        return video_local_url

    if not os.path.exists(LOGO_PATH):
        logger.error(f"process_video_outro: logo not found at {LOGO_PATH}")
        return video_local_url

    # ── Step 0: Check for audio stream presence ───────────────────
    FFPROBE_BIN = shutil.which("ffprobe") or "ffprobe"
    has_audio = False
    try:
        probe_cmd = [
            FFPROBE_BIN, "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True)
        if "audio" in res.stdout:
            has_audio = True
    except Exception as e:
        logger.warning(f"Audio detection failed: {e}. Assuming no audio.")

    # Word-wrap the hook for 1000% safe rendering
    def _wrap_text(text, max_chars=35):
        words = text.split()
        lines = []
        current_line = []
        for w in words:
            if len(" ".join(current_line + [w])) <= max_chars:
                current_line.append(w)
            else:
                lines.append(" ".join(current_line))
                current_line = [w]
        if current_line:
            lines.append(" ".join(current_line))
        return "\n".join(lines[:3]) # Max 3 lines to avoid clutter

    # Robust escaping for FFmpeg drawtext:
    # 1. Backslash, 2. Single Quote, 3. Colon, 4. Percent
    import re
    safe_hook = hook_text.upper()
    
    # Strip ALL non-ASCII characters to prevent square boxes in FFmpeg
    safe_hook = re.sub(r'[^\x00-\x7F]+', '', safe_hook)
    
    # Escape in exact FFmpeg drawtext order:
    # 1. Backslash (must be first), 2. Colon (param separator), 3. Single quote, 4. Comma (filter separator), 5. Semicolon (graph separator), 6. Percent
    safe_hook = safe_hook.replace("\\", "\\\\")       # backslash → \\
    safe_hook = safe_hook.replace(":", "\\:")          # colon → \:
    safe_hook = safe_hook.replace("'", "")             # apostrophe → removed
    safe_hook = safe_hook.replace(",", " ")            # comma → space
    safe_hook = safe_hook.replace(";", " ")            # semicolon → space
    safe_hook = safe_hook.replace("%", "\\%")          # percent → \%
    safe_hook = safe_hook.replace("[", "").replace("]", "")  # brackets break filter graph labels
    safe_hook = _wrap_text(safe_hook)
    # FFmpeg drawtext newline handling: must be escaped as \n string
    safe_hook = safe_hook.replace("\n", "\r")
    
    # Universal Font Fallback
    # On Mac: Helvetica, Avenir
    # On Linux: Arial, DejaVuSans, sans
    FONT_PRIORITY = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "sans"
    ]
    FONT_PATH = "sans"
    for f in FONT_PRIORITY:
        if f.startswith("/") and os.path.exists(f):
            FONT_PATH = f
            logger.info(f"Using font for overlay: {FONT_PATH}")
            break

    # Output path
    output_filename = f"processed_{os.path.basename(video_path)}"
    dest_dir = output_dir or STATIC_DIR
    os.makedirs(dest_dir, exist_ok=True)
    output_path = os.path.join(dest_dir, output_filename)

    # ── Filter: with drawtext hook overlay ──────────────────────────
    # Robust escaping for drawtext parameters
    # Increase visibility range from 0.5s to 9.5s to ensure it's seen
    text_filter_with_hook = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"drawtext=fontfile='{FONT_PATH}':text='{safe_hook}':fontcolor=white:fontsize=45:line_spacing=10:"
        f"box=1:boxcolor=black@0.6:boxborderw=30:x=(w-text_w)/2:y=h*0.75:enable='between(t\\,8\\,12)',"
        f"setsar=1,fps=25,format=yuv420p"
    )

    FFMPEG_BIN = shutil.which("ffmpeg-full") or shutil.which("ffmpeg") or "ffmpeg"
    
    # ── AUDIO HANDLING (Simplified: Restore Original Audio Only) ────────
    # We maintain only the original video audio [0:a] mapping
    audio_source_ref = "[0:a]" if has_audio else "anullsrc=cl=stereo:sr=44100[0a];[0a]"
    
    # ── Choose outro ──────────────────────────────────────────────
    cover_path = None
    if cover_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_cover:
            tmp_cover.write(cover_bytes)
            cover_path = tmp_cover.name

        logo_std_filter = (
            "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,format=yuv420p[v1];"
            "[2:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,format=yuv420p[v2];"
            "[3:a]atrim=0:2[a1];[3:a]atrim=0:1[a2];"
            f"[v0]{audio_source_ref}[v1][a1][v2][a2]concat=n=3:v=1:a=1[outv][outa]"
        )

        def _build_cmd(text_filter):
            return [
                FFMPEG_BIN, "-y",
                "-i", video_path,
                "-loop", "1", "-t", "2", "-i", cover_path,
                "-loop", "1", "-t", "1", "-i", LOGO_PATH,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-filter_complex", f"[0:v]{text_filter}[v0];" + logo_std_filter,
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-shortest",
                output_path
            ]
    else:
        logo_only_filter = (
            "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,format=yuv420p[v1];"
            "[2:a]atrim=0:2[a1];"
            f"[v0]{audio_source_ref}[v1][a1]concat=n=2:v=1:a=1[outv][outa]"
        )

        def _build_cmd(text_filter):
            return [
                FFMPEG_BIN, "-y",
                "-i", video_path,
                "-loop", "1", "-t", "2", "-i", LOGO_PATH,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-filter_complex", f"[0:v]{text_filter}[v0];" + logo_only_filter,
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-shortest",
                output_path
            ]

    # ── Execution ──────────────────────────────────────────────────
    try:
        logger.info(f"Processing video (audio={has_audio}) → {output_filename}")
        cmd = _build_cmd(text_filter_with_hook)
        
        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            logger.warning(f"FFmpeg failed with hook (libfreetype?): {proc.stderr[-500:]}")
            # Fallback to no-hook
            text_filter_no_hook = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p"
            cmd = _build_cmd(text_filter_no_hook)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg failed even on fallback: {proc.stderr[-500:]}")
        
        logger.info(f"Video processing successful.")
    except Exception as e:
        logger.error(f"process_video_outro failed: {e}. Falling back to unbranded FAL video.")
        return video_local_url
    finally:
        if cover_path and os.path.exists(cover_path):
            try:
                os.unlink(cover_path)
            except Exception:
                pass

    return output_path



# ────────────────────────────────────────────────────────────
# Caption Generation via OpenRouter (Async)
# ────────────────────────────────────────────────────────────
async def generate_caption(platform: str, post_concept: str, book_title: str, author_name: str, metadata: dict = {}) -> str:
    """
    Generate a platform-optimized caption for a given post concept.
    """
    platform_prompts = {
        "instagram": INSTAGRAM_CAPTION_PROMPT,
        "linkedin": LINKEDIN_CAPTION_PROMPT,
        "facebook": FACEBOOK_CAPTION_PROMPT,
        "x": X_CAPTION_PROMPT,
    }

    prompt_template = platform_prompts.get(platform.lower())
    if not prompt_template:
        raise ValueError(f"Unknown platform: {platform}")

    # Injecting deep metadata for better grounding
    user_prompt = prompt_template.format(
        book_title=book_title,
        author_name=author_name,
        post_concept=post_concept,
        powerful_line=metadata.get("most_powerful_line", ""),
        human_truth=metadata.get("core_human_truth", ""),
        target_viewer=metadata.get("target_viewer_moment", ""),
        unique_element=metadata.get("unique_world_element", ""),
        genre=metadata.get("primary_genre", "General")
    )

    client = get_openrouter_client()

    # logger.info(f"Generating {platform} caption for: {post_concept[:50]}...")
    
    loop = asyncio.get_event_loop()
    def _run():
        return client.chat.completions.create(
            model="openai/gpt-4o-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": GUARDRAILS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

    response = await loop.run_in_executor(None, _run)
    caption = response.choices[0].message.content.strip()
    return caption


# ────────────────────────────────────────────────────────────
# Post Ideas Generation via OpenRouter
# ────────────────────────────────────────────────────────────
def generate_post_ideas(
    metadata: dict, count: int = 30
) -> list[str]:
    """
    Generate post concepts from the book metadata.
    Returns a list of post concept strings.
    """
    from app.social_media.prompts import POST_IDEAS_PROMPT

    book_title = metadata.get("book_title", "Unknown Title")
    author_name = metadata.get("author_name", "Unknown Author")
    
    # Create a nice summary of the book data for the prompt
    book_data_summary = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in metadata.items() if v])

    user_prompt = POST_IDEAS_PROMPT.format(
        book_title=book_title,
        author_name=author_name,
        book_data=book_data_summary,
    )

    client = get_openrouter_client()

    logger.info(f"Generating {count} post ideas from manuscript...")

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        temperature=0.8,
        max_tokens=1200,
        messages=[
            {"role": "system", "content": GUARDRAILS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Try to parse as JSON array
    try:
        ideas = json.loads(raw)
        if isinstance(ideas, list):
            logger.info(f"Generated {len(ideas)} post ideas")
            return ideas[:count]
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON array from response text
    import re
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            ideas = json.loads(match.group())
            logger.info(f"Generated {len(ideas)} post ideas (regex extracted)")
            return ideas[:count]
        except Exception:
            pass

    logger.warning("Could not parse post ideas as JSON, splitting by newlines")
    # Last resort: split by newlines
    lines = [line.strip().lstrip("-•").strip() for line in raw.split("\n") if line.strip()]
    return lines[:count]
VALID_GENRES = {
    "NONFICTION", "FICTION", "THRILLER",
    "FANTASY", "SCI-FI", "HISTORICAL", "ROMANCE", "LITERARY"
}

async def detect_genre_async(manuscript_text: str) -> str:
    """
    Async version of genre detection.
    """
    from app.social_media.prompts import GENRE_DETECTION_PROMPT
    
    client = get_openrouter_client()
    logger.info("Detecting book genre from manuscript...")

    user_prompt = GENRE_DETECTION_PROMPT.format(
        manuscript_text=manuscript_text[:6_000]
    )

    loop = asyncio.get_event_loop()
    def _call():
        return client.chat.completions.create(
            model="deepseek/deepseek-chat",
            temperature=0.1, # Extremely low for classification
            max_tokens=100,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )

    response = await loop.run_in_executor(None, _call)
    raw = response.choices[0].message.content.strip().upper()
    
    # Filter out common prefixes like "1. " or "GENRE: " if GPT misbehaves
    import re
    clean_genre = re.sub(r'[^A-Z-]', '', raw)
    
    if clean_genre in VALID_GENRES:
        return clean_genre
    
    # Secondary check: search for the keyword in the response
    for g in VALID_GENRES:
        if g in raw:
            return g
            
    logger.warning(f"Ambiguous genre result: '{raw}'. Falling back to NONFICTION.")
    return "NONFICTION"


async def extract_book_metadata_async(manuscript_text: str) -> dict:
    """
    Extract book subtitle and positioning from the manuscript using OpenRouter.
    Returns: {"book_subtitle": "...", "positioning_label": "...", "positioning_desc": "..."}
    """
    from app.social_media.prompts import BOOK_METADATA_PROMPT
    
    client = get_openrouter_client()
    logger.info("Extracting book metadata (subtitle/positioning) from manuscript (50k context)...")

    # INCREASED CONTEXT: 50,000 chars for deeper extraction
    user_prompt = BOOK_METADATA_PROMPT.format(
        manuscript_text=manuscript_text[:50_000] 
    )

    loop = asyncio.get_event_loop()
    def _call():
        return client.chat.completions.create(
            model="deepseek/deepseek-chat",
            temperature=0.3,
            max_tokens=1500,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )

    response = await loop.run_in_executor(None, _call)
    raw = response.choices[0].message.content.strip()

    try:
        data = parse_llm_json(raw)
        
        # PROGRAMMATIC SAFETY NET: Overwrite "None detected" hallucinations
        p_desc = data.get("positioning_desc", "")
        if not p_desc or "none detected" in p_desc.lower() or "n/a" == p_desc.lower():
            logger.warning("LLM returned 'None detected' for positioning. Synthesizing fallback.")
            data["positioning_desc"] = "A narrative exploration of human relationships and transformation."
            
        subtitle = data.get("book_subtitle", "")
        if not subtitle or "none detected" in subtitle.lower() or "n/a" == subtitle.lower():
            data["book_subtitle"] = "A journey of transformation and discovery."
            
        return data
    except Exception:
        pass

    logger.warning("Could not extract book metadata as JSON. Using fallbacks.")
    return {
        "book_subtitle": "A story of discovery.",
        "positioning_label": "THEMATIC",
        "positioning_desc": "An evocative exploration of characters and themes."
    }


# ────────────────────────────────────────────────────────────
# UTILITIES
# ────────────────────────────────────────────────────────────
async def call_llm(system_prompt: str, user_content: str, model: str = "deepseek/deepseek-chat", temperature: float = 0.7) -> str:
    """
    Helper to call OpenRouter LLM with provided prompts.
    """
    client = get_openrouter_client()
    loop = asyncio.get_event_loop()
    
    def _call():
        return client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
    
    response = await loop.run_in_executor(None, _call)
    return response.choices[0].message.content.strip()

# ============================================================
# IMAGE PIPELINE (Stage 1 + 2 + 3)
# ============================================================

async def generate_image_concepts_pipeline(
    manuscript_text: str,
    metadata: dict,
    num_concepts: int = 15
) -> list:
    """
    Full image pipeline: Extraction → Ranking → Ready-to-use concepts
    Returns list of ranked image concepts
    """
    logger.info(f"[IMAGE PIPELINE] Starting concept extraction for {metadata.get('book_title')}")
    
    # Stage 1: Extract concepts from manuscript
    extraction_prompt = IMAGE_EXTRACTION_PROMPT.format(
        book_title=metadata.get("book_title", "Unknown"),
        primary_genre=metadata.get("primary_genre", "FICTION"),
        positioning_desc=metadata.get("positioning_desc", ""),
        book_subtitle=metadata.get("book_subtitle", "")
    )
    
    # Use first 8000 chars of manuscript for context
    manuscript_sample = manuscript_text[:8000] if manuscript_text else ""
    
    extraction_response = await call_llm(
        system_prompt=extraction_prompt,
        user_content=manuscript_sample
    )
    
    concepts = parse_llm_json(extraction_response)
    
    # Validation: Ensure result is a list
    if isinstance(concepts, dict) and "concepts" in concepts:
        concepts = concepts["concepts"]
    
    if not concepts or not isinstance(concepts, list):
        logger.warning("[IMAGE PIPELINE] Extraction failed or returned invalid format, using fallback concepts")
        concepts = generate_fallback_concepts(metadata, num_concepts)
    
    logger.info(f"[IMAGE PIPELINE] Extracted {len(concepts)} concepts")
    
    # Stage 2: Rank concepts
    ranking_prompt = IMAGE_RANKING_PROMPT.format(
        concepts_json=json.dumps(concepts[:30])  # Send up to 30 for ranking
    )
    
    ranking_response = await call_llm(
        system_prompt=ranking_prompt,
        user_content="Rank these concepts by marketing effectiveness and diversity."
    )
    
    ranking_data = parse_llm_json(ranking_response)
    
    if ranking_data and "ranked_concepts" in ranking_data:
        ranked_concepts = ranking_data["ranked_concepts"]
        logger.info(f"[IMAGE PIPELINE] Ranking complete, diversity audit: {ranking_data.get('diversity_audit', 'N/A')}")
    else:
        logger.warning("[IMAGE PIPELINE] Ranking failed, using original order")
        ranked_concepts = concepts[:num_concepts]
    
    # Return top N concepts
    return ranked_concepts[:num_concepts]


def generate_fallback_concepts(metadata: dict, count: int) -> list:
    """Generate fallback concepts when extraction fails"""
    book_title = metadata.get("book_title", "The Book")
    genre = metadata.get("primary_genre", "FICTION")
    
    fallback_concepts = []
    
    # Create variations based on genre
    genre_variations = {
        "FANTASY": ["mysterious", "enchanted", "ancient", "magical"],
        "FICTION": ["contemplative", "atmospheric", "intimate", "poetic"],
        "ROMANCE": ["romantic", "tender", "passionate", "intimate"],
        "THRILLER": ["dark", "suspenseful", "tense", "shadowy"],
        "SELF_HELP": ["calm", "focused", "motivational", "peaceful"],
        "BUSINESS": ["professional", "dynamic", "corporate", "premium"],
        "LANGUAGE": ["inviting", "cultural", "warm", "adventurous"]
    }
    
    moods = genre_variations.get(genre, ["contemplative", "atmospheric", "intimate"])
    
    for i in range(min(count, 15)):
        # Cycle through categories
        if i < 4:
            category = "book_cover"
        elif i < 8:
            category = "quote"
        elif i < 12:
            category = "available_now"
        else:
            category = "coming_soon"
        
        base = FALLBACK_IMAGE_CONCEPTS.get(category, FALLBACK_IMAGE_CONCEPTS["book_cover"]).copy()
        
        # Slightly customize for diversity
        mood_idx = i % len(moods)
        base["emotion"] = moods[mood_idx]
        
        if i % 3 == 0:
            base["placement"] = base["placement"].replace("resting on", "rising from shadows")
        elif i % 3 == 1:
            base["placement"] = base["placement"].replace("resting on", "leaning against")
        
        fallback_concepts.append(base)
    
    return fallback_concepts


async def generate_single_image(
    payload: dict
) -> str:
    """
    Generate a single image using fal-ai/flux-2-pro/edit using a pre-built payload
    Returns image URL
    """
    
    # Call FAL API
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://fal.run/fal-ai/flux-2-pro/edit",
            json=payload,
            headers={"Authorization": f"Key {os.environ.get('FAL_KEY')}"}
        ) as response:
            if response.status != 200:
                err_text = await response.text()
                logger.error(f"FAL API Error ({response.status}): {err_text}")
                return ""
            result = await response.json()
            return result.get("images", [{}])[0].get("url", "")

def parse_llm_json(content: str) -> dict:
    """
    Robustly parse JSON from LLM output, stripping markdown fences if present.
    Includes regex fallback to find the first JSON object or array.
    """
    import re
    if not content:
        return {}
        
    cleaned = content.strip()
    
    # 1. Strip markdown fences or any conversational filler
    if "```" in cleaned:
        # Try specific 'json' fence first
        match = re.search(r"```json\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
        if not match:
            # Fallback to generic fence
            match = re.search(r"```\s*(.*?)```", cleaned, re.DOTALL)
        
        if match:
            cleaned = match.group(1).strip()
    
    # Cleanup common LLM messiness
    cleaned = cleaned.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    
    # Try to fix unescaped newlines inside strings (common in LLMs)
    # This regex looks for newlines that are not preceded by a comma/brace/bracket/quote and not followed by a quote
    cleaned = re.sub(r'([^\,\[\{\:\"\s])\n\s*([^\,\]\}\:\"\s])', r'\1 \2', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to fix trailing commas and other common issues
        try:
            # Simple trailing comma fix (for lists/objects)
            cleaned_fix = re.sub(r",\s*([\]}])", r"\1", cleaned)
            return json.loads(cleaned_fix)
        except:
            pass

    # 2. Regex fallback (detect common JSON structures)
    match_arr = re.search(r"(\[.*\])", cleaned, re.DOTALL)
    if not match_arr:
        # Try to find a partial/truncated array (starts with [ and maybe has some {} inside)
        match_arr_partial = re.search(r"(\[.*)", cleaned, re.DOTALL)
        if match_arr_partial:
            candidate = match_arr_partial.group(1).strip()
            # If it's a list that doesn't end with ], try to close it
            if not candidate.endswith("]"):
                last_obj = candidate.rfind("}")
                if last_obj != -1:
                    candidate = candidate[:last_obj+1] + "]"
                    try:
                        return json.loads(candidate)
                    except: pass
    else:
        try:
            return json.loads(match_arr.group(1))
        except:
            # Try to fix truncated JSON if it's an array
            try:
                candidate = match_arr.group(1).strip()
                if not candidate.endswith("]"):
                    # Attempt to find last valid object and close it
                    last_obj = candidate.rfind("}")
                    if last_obj != -1:
                        candidate = candidate[:last_obj+1] + "]"
                        return json.loads(candidate)
            except: pass

    match_obj = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match_obj:
        try:
            return json.loads(match_obj.group(1))
        except Exception as e:
            logger.debug(f"Regex object match failed to parse: {e}")
            
    # Final attempt: manual cleanup of common LLM artifacts
    try:
        # Extreme cleanup: replace any \n followed by " with "
        fixed = re.sub(r'\n\s*"', '"', cleaned)
        return json.loads(fixed)
    except Exception:
        pass
        
    return {}

    logger.error(f"Failed to parse LLM JSON. Raw content: {content[:500]}...")
    raise ValueError(f"Invalid JSON format from LLM: {content[:100]}...")

# ────────────────────────────────────────────────────────────
def clean_video_prompt(prompt: str) -> str:
    """
    Hardens the video prompt for Seedance/FAL compatibility:
    1. Removes bracket placeholders: [LABEL: content] -> content
    2. Flattens all line breaks into a single string
    3. Tones down over-cinematic/physics-defying language
    4. Ensures clean whitespace
    """
    import re
    
    # 1. Strip bracket placeholders while keeping inner content
    # Handles [LABEL: content] -> content or [content] -> content
    prompt = re.sub(r'\[(?:[^:\]]+:)?\s*([^\]]+)\]', r'\1', prompt)
    
    # 2. Flatten newlines
    prompt = prompt.replace('\n', ' ')
    
    # 3. Word Filter (User specified & Zero-Text Hardening)
    replacements = {
        r'\bexploding\b': 'spraying',
        r'\bsuspended arcs\b': 'upward',
        r'\btrailing ice dust\b': 'ice dust',
        r'\bcrystalline fragments\b': 'ice fragments',
        r'\bsmooth downswing\b': 'downswing',
        r'\bsmooth collision\b': 'collision',
        r'\bsmooth impact\b': 'impact',
        # Zero-Text Hardening
        r'\bstop name\b': 'unreadable route markings',
        r'\bprice tag\b': 'blurry symbol',
        r'\bwritten\b': 'marked',
        r'\btext\b': 'markings',
        r'\blabel\b': 'blurry label',
        r'\bnaming\b': 'marking',
        r'\bwords\b': 'symbols',
        r'\bletters\b': 'markings',
        r'\bnumbers\b': 'blurry markings',
        r'\bchalkboard\b': 'dark surface with unreadable markings',
        r'\bboard\b': 'surface',
        r'\bsign\b': 'unreadable sign',
        r'\bflashcard\b': 'small card with unreadable markings',
        # Visual Symbol Hardening (Status replacement)
        r'\brejected\b': 'marked with a red cross',
        r'\baccepted\b': 'marked with a green mark',
        r'\bstatus\b': 'markings',
        r'\bname\b': 'markings',
        # Style Cleanup (No-Dash & No-Directional-Filler)
        r'\bas the movement completes\b': '',
        r'\bin one sharp motion\b': '',
        r'\bfocusing on the\b': '',
        # Strip all types of dashes/hyphens and replace with comma/space
        r'[-—]': ' ',
    }
    
    for pattern, replacement in replacements.items():
        prompt = re.sub(pattern, replacement, prompt, flags=re.IGNORECASE)
        
    # 4. Final Cleanup
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    
    # 5. Length Enforcement (~600 chars for complete concepts)
    # If "Voiceover syncs with" is present, we must preserve it.
    LIMIT = 650 # Allow up to 650 to be safe
    if len(prompt) > LIMIT:
        if "Voiceover syncs with" in prompt:
            parts = prompt.split("Voiceover syncs with")
            visual_part = parts[0].strip()
            vo_part = "Voiceover syncs with" + parts[1]
            allowed_visual = LIMIT - len(vo_part) - 10
            if allowed_visual > 50:
                prompt = visual_part[:allowed_visual].rsplit(' ', 1)[0] + "... " + vo_part
        else:
            # Simple truncation at last word
            prompt = prompt[:LIMIT].rsplit(' ', 1)[0] + "..."
            
    return prompt


# Video Concepts Generation via OpenRouter
# ────────────────────────────────────────────────────────────
async def generate_video_prompt_pipeline(manuscript_text: str, metadata: dict, requested_video_count: int = 1, iteration: int = 0) -> list[dict]:
    """
    Full multi-stage pipeline:
    Extraction → Scenario → Ranking → [Loop: Hook → Cinematic]
    Generates multiple prompts if requested_video_count > 1.
    """

    client = get_openrouter_client()
    loop = asyncio.get_event_loop()

    # ───────────────── STAGE 1: EXTRACTION ─────────────────
    def _extract():
        def get_safe_metadata(metadata, key, fallback="Not provided"):
            value = metadata.get(key, fallback)
            if not value or (isinstance(value, list) and len(value) == 0):
                return fallback
            return value

        # Calculate dynamic moment count: N * 2.5 (rounded up), min 4, max 15
        import math
        moment_count = min(max(math.ceil(requested_video_count * 2.5), 4), 15)
        logger.info(f"[VIDEO PIPELINE] Dynamic extraction: asking for {moment_count} moments (for {requested_video_count} videos)")

        formatted_extraction_prompt = (
            VIDEO_EXTRACTION_PROMPT
            .replace("{book_title}", metadata.get("book_title", "Unknown"))
            .replace("{primary_genre}", metadata.get("primary_genre", "Fiction"))
            .replace("{positioning_desc}", metadata.get("positioning_desc", "Cultural identity and familial expectations."))
            .replace("{book_subtitle}", metadata.get("book_subtitle", ""))
            .replace("{moment_count}", str(moment_count))
            .replace("{repeatable_moments}", json.dumps(get_safe_metadata(metadata, "repeatable_moments", [])))
            .replace("{unique_world_element}", get_safe_metadata(metadata, "unique_world_element", "Not provided"))
            .replace("{before_state_visual}", get_safe_metadata(metadata, "before_state_visual", "Not provided"))
            .replace("{after_state_one_line}", get_safe_metadata(metadata, "after_state_one_line", "Not provided"))
        )

        temperature = min(0.2 + (iteration * 0.1), 0.6)
        logger.info(f"[VIDEO PIPELINE] Extraction temperature: {temperature} (iteration {iteration})")

        return client.chat.completions.create(
            model="deepseek/deepseek-chat",
            temperature=temperature,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": formatted_extraction_prompt},
                {"role": "user", "content": manuscript_text[:8000]},
            ],
        )

    extraction_res = await loop.run_in_executor(None, _extract)
    extraction_output = extraction_res.choices[0].message.content.strip()
    
    # ── HANDLE STATUS ──
    try:
        extraction_data = parse_llm_json(extraction_output)
    except Exception:
        logger.error(f"[VIDEO PIPELINE] Extraction returned invalid JSON: {extraction_output[:200]}...")
        raise RuntimeError("Extraction failed: invalid JSON")

    status = extraction_data.get("status", "success")
    if status == "non_narrative":
        logger.warning(f"[VIDEO PIPELINE] Extraction status: non_narrative. Reason: {extraction_data.get('reason', 'Unknown')}")
        raise ValueError(f"Book is not cinematic enough: {extraction_data.get('reason', 'No reason provided')}")

    moments = extraction_data.get("moments", [])
    if not moments:
        logger.warning("[VIDEO PIPELINE] No moments found in extraction.")
        raise ValueError("No extractable moments found.")

    logger.info(f"[VIDEO PIPELINE] Extraction done. Found {len(moments)} moments.")

    # ───────────────── STAGE 2: SCENARIO ─────────────────
    def _scenario():
        return client.chat.completions.create(
            model="deepseek/deepseek-chat",
            temperature=0.8,
            max_tokens=2500,
            messages=[
                {"role": "system", "content": VIDEO_SCENARIO_PROMPT},
                {"role": "user", "content": json.dumps(moments)},
            ],
        )

    scenario_res = await loop.run_in_executor(None, _scenario)
    scenario_output = scenario_res.choices[0].message.content.strip()

    try:
        scenario_data = parse_llm_json(scenario_output)
    except Exception:
        logger.error(f"[VIDEO PIPELINE] Scenario returned invalid JSON: {scenario_output[:200]}...")
        raise RuntimeError("Scenario generation failed: invalid JSON")

    if isinstance(scenario_data, list):
        scenarios = scenario_data
    else:
        scenarios = scenario_data.get("scenarios", [])

    if not scenarios:
        if moments:
            logger.warning("[VIDEO PIPELINE] Scenario layer failed to generate scenarios. Falling back to raw moments.")
            scenarios = [{"visual_script": m.get("action", "A cinematic scene."), "object": m.get("object", "object"), "consequence": m.get("consequence", "")} for m in moments]
        else:
            raise ValueError("No scenarios generated from extraction.")

    logger.info(f"[VIDEO PIPELINE] Scenario done. [SCENARIOS COUNT]: {len(scenarios)}")

    # ───────────────── STAGE 3: RANKING ─────────────────
    def _ranking():
        return client.chat.completions.create(
            model="deepseek/deepseek-chat",
            temperature=0.2,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": VIDEO_RANKING_PROMPT},
                {"role": "user", "content": json.dumps(scenarios)},
            ],
        )

    ranking_res = await loop.run_in_executor(None, _ranking)
    ranking_output = ranking_res.choices[0].message.content.strip()

    try:
        ranking_data = parse_llm_json(ranking_output)
    except Exception:
        logger.error(f"[VIDEO PIPELINE] Ranking returned invalid JSON: {ranking_output[:200]}...")
        raise RuntimeError("Ranking generation failed: invalid JSON")

    if isinstance(ranking_data, list):
        top_scenarios = ranking_data
    else:
        top_scenarios = ranking_data.get("top_scenarios", [])

    if not top_scenarios:
        if isinstance(ranking_data, list) and len(ranking_data) > 0:
             top_scenarios = ranking_data[:2]
        else:
            raise ValueError("No top scenarios found in ranking.")

    logger.info(f"[VIDEO PIPELINE] Ranking done. [TOP SCENARIOS COUNT]: {len(top_scenarios)}")

    # ───────────────── STAGE 4+5: PARALLEL LOOP ─────────────────
    all_results = []
    
    async def _process_single_video(idx):
        # Cycle through scenarios if we need more videos than we have top ones
        scenario_idx = idx % len(top_scenarios)
        selected_scenario = top_scenarios[scenario_idx]
        
        if not isinstance(selected_scenario, dict):
            if isinstance(selected_scenario, str):
                selected_scenario = {"visual_script": selected_scenario, "action": selected_scenario}
            else:
                selected_scenario = {"visual_script": "A cinematic moment.", "action": "Unknown action"}

        logger.info(f"[VIDEO PIPELINE] Parallel start: prompt {idx+1}/{requested_video_count} (scenario #{scenario_idx})")

        # Stage 4: Hook
        def _hook():
            return client.chat.completions.create(
                model="deepseek/deepseek-chat",
                temperature=0.7,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": VIDEO_HOOK_PROMPT},
                    {
                        "role": "user",
                        "content": f"Genre: {metadata.get('primary_genre', 'GENERAL')}\nScenario: {selected_scenario.get('visual_script', selected_scenario.get('action', str(selected_scenario)))}",
                    },
                ],
            )

        hook_res = await loop.run_in_executor(None, _hook)
        hook_output = hook_res.choices[0].message.content.strip()
        
        try:
            hook_data = parse_llm_json(hook_output)
            hook_text = hook_data.get("hook", "A cinematic revelation.")
            sync_action_guide = hook_data.get("sync_action", "the failure")
        except Exception:
            hook_text = hook_output.replace('"', '')
            sync_action_guide = "the action"

        hook_text = hook_text.replace('"', '').replace('"', '')
        
        # Stage 5: Cinematic
        def _cinematic():
            cinematic_user_content = {
                "scenario": selected_scenario,
                "hook_text_to_bake_in": hook_text,
                "sync_action_guide": sync_action_guide,
                "book_title": metadata.get("book_title", "Unknown"),
                "author_name": metadata.get("author_name", "Unknown")
            }
            return client.chat.completions.create(
                model="deepseek/deepseek-chat",
                temperature=0.5,
                max_tokens=3000,
                messages=[
                    {"role": "system", "content": VIDEO_CINEMATIC_PROMPT},
                    {"role": "user", "content": json.dumps(cinematic_user_content)},
                ],
            )

        cinematic_res = await loop.run_in_executor(None, _cinematic)
        cinematic_output = cinematic_res.choices[0].message.content.strip()
        
        # Safety fallback
        if not cinematic_output or len(cinematic_output) < 60:
            btitle = metadata.get("book_title", "this book")
            aname = metadata.get("author_name", "the author")
            cinematic_output = (
                f"A cinematic slow dolly-in of a hand gathering an object, "
                f"in a quiet room, focusing on a failed interaction — as the hand drops, "
                f"a voice says '{hook_text} {btitle} by {aname}', soft natural lighting, shallow depth of field, "
                f"photorealistic, smooth motion, mood unresolved. Ambient sound of room tone and soft piano."
            )
        
        final_prompt = clean_video_prompt(cinematic_output)
        
        return {
            "fal_prompt": final_prompt,
            "hook": hook_text,
            "iteration": iteration + idx
        }

    # Parallelize execution for all requested videos
    tasks = [_process_single_video(i) for i in range(requested_video_count)]
    all_results = await asyncio.gather(*tasks)

    return all_results


# generate_image_concepts_async removed — superseded by generate_image_prompt_pipeline
    
