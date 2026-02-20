from fastapi import APIRouter
import pymysql
from app.database import get_connection

router = APIRouter()

@router.get("/campaigns")
def get_campaigns():
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    query = """
    SELECT 
        c.campaignId,
        c.name,
        c.state,
        c.startDate,
        c.endDate,
        c.budget,
        c.budgetType,
        c.targetingType,

        CASE
            WHEN c.targetingType = 'AUTO' THEN 'AUTO'

            WHEN c.targetingType = 'MANUAL' 
                 AND EXISTS (
                    SELECT 1
                    FROM sp_targeting_reports t
                    WHERE t.campaign_id = c.campaignId
                    AND t.keyword_type = 'TARGETING_EXPRESSION'
                 )
            THEN 'PROD'

            WHEN c.targetingType = 'MANUAL' 
                 AND EXISTS (
                    SELECT 1
                    FROM sp_targeting_reports t
                    WHERE t.campaign_id = c.campaignId
                    AND t.keyword_type IN ('BROAD','PHRASE','EXACT')
                 )
            THEN 'KEY'

            ELSE 'UNKNOWN'
        END AS type

    FROM campaigns c

    ORDER BY c.startDate DESC
    """

    cursor.execute(query)
    campaigns = cursor.fetchall()

    cursor.close()
    conn.close()

    return campaigns
