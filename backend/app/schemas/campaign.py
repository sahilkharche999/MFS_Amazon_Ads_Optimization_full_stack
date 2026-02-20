from pydantic import BaseModel
from datetime import date
from typing import Optional

class CampaignResponse(BaseModel):
    campaignId: int
    name: Optional[str]
    state: Optional[str]
    targetingType: Optional[str]
    startDate: Optional[date]
    endDate: Optional[date]
    budget: Optional[float]
    budgetType: Optional[str]

    class Config:
        from_attributes = True
