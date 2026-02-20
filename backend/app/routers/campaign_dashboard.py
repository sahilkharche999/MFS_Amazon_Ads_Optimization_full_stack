from fastapi import APIRouter
from app.database import get_connection
import pymysql

router = APIRouter()

@router.get("/campaign/{campaign_id}/dashboard")
def get_campaign_dashboard(campaign_id: str, start_date: str, end_date: str):

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get campaign info
    cursor.execute("""
        SELECT name, targetingType
        FROM campaigns
        WHERE campaignId = %s
    """, (campaign_id,))
    
    campaign = cursor.fetchone()

    if not campaign:
        return {
            "campaign_name": "Unknown Campaign",
            "type": "UNKNOWN",
            "data": []
        }

    campaign_name = campaign["name"]
    targeting_type = campaign["targetingType"]

    # AUTO campaigns
    if targeting_type == "AUTO":
        subtype = "AUTO"
        filter_clause = "keyword_type = 'TARGETING_EXPRESSION_PREDEFINED'"

    else:
        # Detect subtype dynamically
        cursor.execute("""
            SELECT DISTINCT keyword_type
            FROM sp_targeting_reports
            WHERE campaign_id = %s
        """, (campaign_id,))
        
        keyword_types = [row["keyword_type"] for row in cursor.fetchall()]

        if any(kt in ["BROAD","PHRASE","EXACT"] for kt in keyword_types):
            subtype = "KEY"
            filter_clause = "keyword_type IN ('BROAD','PHRASE','EXACT')"

        elif "TARGETING_EXPRESSION" in keyword_types:
            subtype = "PROD"
            filter_clause = "keyword_type = 'TARGETING_EXPRESSION'"

        else:
            subtype = "UNKNOWN"
            filter_clause = "1=0"

    query = f"""
    SELECT
        target_id AS entityId,
        targeting AS entityText,
        MAX(keyword_bid) AS bid,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(cost) AS ad_spend,
        SUM(purchases_7d) AS purchases,

        CASE
            WHEN SUM(impressions) = 0 THEN 0
            ELSE ROUND(SUM(clicks) / SUM(impressions) * 100, 2)
        END AS ctr_percent,

        CASE
            WHEN SUM(purchases_7d) = 0 THEN 0
            ELSE ROUND(SUM(cost) / SUM(purchases_7d), 2)
        END AS cost_per_order

    FROM sp_targeting_reports
    WHERE campaign_id = %s
    AND report_date BETWEEN %s AND %s
    AND {filter_clause}

    GROUP BY target_id, targeting
    ORDER BY ad_spend DESC
    """

    cursor.execute(query, (campaign_id, start_date, end_date))
    results = cursor.fetchall()

    cursor.execute("""
    SELECT
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(cost) AS spend,
        SUM(purchases_7d) AS orders
    FROM sp_targeting_reports
    WHERE campaign_id = %s
    AND report_date BETWEEN %s AND %s
    """, (campaign_id, start_date, end_date))

    summary = cursor.fetchone()

    cursor.execute("""
    SELECT
        report_date AS date,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(cost) AS spend,
        SUM(purchases_7d) AS orders
    FROM sp_targeting_reports
    WHERE campaign_id = %s
    AND report_date BETWEEN %s AND %s
    GROUP BY report_date
    ORDER BY report_date
    """, (campaign_id, start_date, end_date))

    trend = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
    "campaign_name": campaign_name,
    "type": subtype,
    "data": results,
    "summary": summary,
    "trend": trend
    }
