from fastapi import APIRouter, Request
import pymysql
from app.database import get_connection
import logging
import traceback
import time

router = APIRouter()

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("campaigns")


@router.get("/campaigns")
def get_campaigns(request: Request):

    start_time = time.time()

    logger.info("========== GET CAMPAIGNS ENDPOINT HIT ==========")
    logger.info(f"Request URL: {request.url}")

    try:
        logger.info("Opening database connection")
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        logger.info("Executing campaigns query")

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

        logger.info(f"Fetched {len(campaigns)} campaigns from database")

        cursor.close()
        conn.close()
        logger.info("Database connection closed")

        execution_time = round(time.time() - start_time, 3)
        logger.info(f"Get campaigns completed in {execution_time} seconds")
        logger.info("========== GET CAMPAIGNS END ==========")

        return campaigns

    except Exception as e:
        logger.error("ERROR in get_campaigns endpoint")
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise