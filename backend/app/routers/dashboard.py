from fastapi import APIRouter, Request
from app.database import get_connection
import pymysql
import logging
import traceback
import time

router = APIRouter()

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("dashboard")


# ======================
# SUMMARY KPIs
# ======================
@router.get("/dashboard/summary")
def get_dashboard_summary(request: Request):

    start_time = time.time()

    logger.info("========== DASHBOARD SUMMARY ENDPOINT HIT ==========")
    logger.info(f"Request URL: {request.url}")

    try:
        logger.info("Opening database connection")
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        logger.info("Executing 14-day summary KPI query")

        query = """
        SELECT 
            COALESCE(SUM(impressions),0) as impressions,
            COALESCE(SUM(clicks),0) as clicks,
            COALESCE(SUM(spend),0) as spend,
            COALESCE(SUM(purchases14d),0) as orders,
            COALESCE(SUM(sales14d),0) as sales
        FROM campaign_performance_daily
        WHERE date >= CURDATE() - INTERVAL 14 DAY
        """

        cursor.execute(query)
        result = cursor.fetchone()

        logger.info("Summary query executed successfully")
        logger.info(f"Summary result: {result}")

        cursor.close()
        conn.close()
        logger.info("Database connection closed")

        execution_time = round(time.time() - start_time, 3)
        logger.info(f"Dashboard summary completed in {execution_time} seconds")
        logger.info("========== DASHBOARD SUMMARY END ==========")

        return result

    except Exception as e:
        logger.error("ERROR in dashboard summary endpoint")
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise


# ======================
# 14 DAY TREND
# ======================
@router.get("/dashboard/trend")
def get_dashboard_trend(request: Request):

    start_time = time.time()

    logger.info("========== DASHBOARD TREND ENDPOINT HIT ==========")
    logger.info(f"Request URL: {request.url}")

    try:
        logger.info("Opening database connection")
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        logger.info("Executing 14-day trend query")

        query = """
        SELECT
            date,
            COALESCE(SUM(impressions),0) as impressions,
            COALESCE(SUM(clicks),0) as clicks,
            COALESCE(SUM(spend),0) as spend,
            COALESCE(SUM(purchases14d),0) as orders
        FROM campaign_performance_daily
        WHERE date >= CURDATE() - INTERVAL 14 DAY
        GROUP BY date
        ORDER BY date
        """

        cursor.execute(query)
        results = cursor.fetchall()

        logger.info(f"Trend query returned {len(results)} rows")

        cursor.close()
        conn.close()
        logger.info("Database connection closed")

        execution_time = round(time.time() - start_time, 3)
        logger.info(f"Dashboard trend completed in {execution_time} seconds")
        logger.info("========== DASHBOARD TREND END ==========")

        return results

    except Exception as e:
        logger.error("ERROR in dashboard trend endpoint")
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise