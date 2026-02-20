from sqlalchemy import Column, BigInteger, String, Date, Numeric, JSON
from app.database import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    campaignId = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255))
    state = Column(String(50))
    targetingType = Column(String(50))
    startDate = Column(Date)
    endDate = Column(Date)
    budget = Column(Numeric(10, 2))
    budgetType = Column(String(50))
    biddingStrategy = Column(String(100))
    marketplaceBudgetAllocation = Column(String(100))
    raw_json = Column(JSON)