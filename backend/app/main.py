from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import campaigns, campaign_dashboard, dashboard, optimize_campaign

app = FastAPI()

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router, prefix="/api")
app.include_router(campaign_dashboard.router, prefix="/api")
app.include_router(optimize_campaign.router, prefix="/api") 
app.include_router(dashboard.router, prefix="/api")

