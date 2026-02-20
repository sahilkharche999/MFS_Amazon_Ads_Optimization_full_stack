from fastapi import APIRouter
from app.database import get_connection
import pymysql

router = APIRouter()

# ======================
# SUMMARY KPIs
# ======================
@router.get("/dashboard/summary")
def get_dashboard_summary():
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
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

    cursor.close()
    conn.close()

    return result


# ======================
# 14 DAY TREND
# ======================
@router.get("/dashboard/trend")
def get_dashboard_trend():
    conn = get_connection()
    cursor =  conn.cursor(pymysql.cursors.DictCursor)

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

    cursor.close()
    conn.close()

    return results
