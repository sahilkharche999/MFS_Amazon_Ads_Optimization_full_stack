from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file (check current and parent dir)
target_env = None
if os.path.exists(".env"):
    target_env = ".env"
elif os.path.exists("../.env"):
    target_env = "../.env"

if target_env:
    load_dotenv(target_env)
else:
    load_dotenv()

from app.routers import campaigns, campaign_dashboard, dashboard, optimize_campaign
from app.social_media import router as social_media_router
import logging
import time
import traceback

# ================= GLOBAL LOGGING CONFIG =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("main")

app = FastAPI()

# ================= CORS CONFIG =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

logger.info("CORS middleware and static files configured")

# ================= GLOBAL REQUEST LOGGER =================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    logger.info(f"Incoming Request: {request.method} {request.url}")

    try:
        response = await call_next(request)

        process_time = round(time.time() - start_time, 3)

        logger.info(
            f"Completed: {request.method} {request.url} "
            f"Status: {response.status_code} "
            f"Time: {process_time}s"
        )

        # ── ENSURE CORS FOR STATIC FILES (Canvas/Fetch Safety) ──
        if request.url.path.startswith("/static"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"

        return response

    except Exception as e:
        logger.error("Unhandled exception during request")
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise


# ================= STARTUP / SHUTDOWN EVENTS =================
@app.on_event("startup")
async def startup_event():
    logger.info("========== APPLICATION STARTED ==========")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("========== APPLICATION SHUTDOWN ==========")


# ================= ROUTERS =================
app.include_router(campaigns.router, prefix="/api")
app.include_router(campaign_dashboard.router, prefix="/api")
app.include_router(optimize_campaign.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(social_media_router.router, prefix="/api")

logger.info("All routers registered successfully")