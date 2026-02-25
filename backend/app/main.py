from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import campaigns, campaign_dashboard, dashboard, optimize_campaign
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

logger.info("CORS middleware configured")

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

logger.info("All routers registered successfully")