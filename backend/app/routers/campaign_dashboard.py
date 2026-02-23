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
            "data": [],
            "summary": {},
            "trend": []
        }

    campaign_name = campaign["name"]
    targeting_type = campaign["targetingType"]

    # Derive subtype from name first
    name_upper = campaign_name.upper()

    if "KEY" in name_upper:
        subtype = "KEY"
    elif "AUTO" in name_upper:
        subtype = "AUTO"
    elif "PROD" in name_upper:
        subtype = "PROD"
    else:
        if targeting_type == "AUTO":
            subtype = "AUTO"
        else:
            cursor.execute("""
                SELECT DISTINCT keyword_type
                FROM sp_targeting_reports
                WHERE campaign_id = %s
            """, (campaign_id,))
            keyword_types = [row["keyword_type"] for row in cursor.fetchall()]

            if any(kt in ["BROAD", "PHRASE", "EXACT"] for kt in keyword_types):
                subtype = "KEY"
            elif "TARGETING_EXPRESSION" in keyword_types:
                subtype = "PROD"
            elif "TARGETING_EXPRESSION_PREDEFINED" in keyword_types:
                subtype = "AUTO"
            else:
                subtype = None

    
    # Get dashboard data
    # ========= KEY Campaign =========
    if subtype == "KEY":

        query = """
        SELECT
            k.keywordId AS entityId,
            k.keywordText AS entityText,
            k.bid AS bid,

            COALESCE(SUM(p.impressions),0) AS impressions,
            COALESCE(SUM(p.clicks),0) AS clicks,
            COALESCE(SUM(p.cost),0) AS ad_spend,
            COALESCE(SUM(p.purchases14d),0) AS purchases,

            CASE
                WHEN COALESCE(SUM(p.impressions),0)=0 THEN 0
                ELSE ROUND(SUM(p.clicks)/SUM(p.impressions)*100,2)
            END AS ctr_percent,

            CASE
                WHEN COALESCE(SUM(p.purchases14d),0)=0 THEN 0
                ELSE ROUND(SUM(p.cost)/SUM(p.purchases14d),2)
            END AS cost_per_order

        FROM keywords k

        LEFT JOIN keyword_performance_full p
            ON k.keywordId = p.keywordId
            AND p.date BETWEEN %s AND %s

        WHERE k.campaignId = %s

        GROUP BY k.keywordId, k.keywordText, k.bid
        ORDER BY ad_spend DESC
        """

        cursor.execute(query, (start_date, end_date, campaign_id))
        results = cursor.fetchall()

        # Summary
        cursor.execute("""
            SELECT
                COALESCE(SUM(impressions),0) AS impressions,
                COALESCE(SUM(clicks),0) AS clicks,
                COALESCE(SUM(cost),0) AS spend,
                COALESCE(SUM(purchases14d),0) AS orders
            FROM keyword_performance_full
            WHERE campaignId = %s
            AND date BETWEEN %s AND %s
        """, (campaign_id, start_date, end_date))

        summary = cursor.fetchone()

        # Trend
        cursor.execute("""
            SELECT
                date AS date,
                COALESCE(SUM(impressions),0) AS impressions,
                COALESCE(SUM(clicks),0) AS clicks,
                COALESCE(SUM(cost),0) AS spend,
                COALESCE(SUM(purchases14d),0) AS orders
            FROM keyword_performance_full
            WHERE campaignId = %s
            AND date BETWEEN %s AND %s
            GROUP BY date
            ORDER BY date
        """, (campaign_id, start_date, end_date))

        trend = cursor.fetchall()

    # ========= AUTO / PROD =========
    else:

        query ="""
        SELECT
            t.target_id AS entityId,
            t.readable_expression AS entityText,
            t.bid AS bid,

            COALESCE(SUM(r.impressions),0) AS impressions,
            COALESCE(SUM(r.clicks),0) AS clicks,
            COALESCE(SUM(r.cost),0) AS ad_spend,
            COALESCE(SUM(r.purchases_14d),0) AS purchases,

            CASE
                WHEN COALESCE(SUM(r.impressions),0)=0 THEN 0
                ELSE ROUND(SUM(r.clicks)/SUM(r.impressions)*100,2)
            END AS ctr_percent,

            CASE
                WHEN COALESCE(SUM(r.purchases_14d),0)=0 THEN 0
                ELSE ROUND(SUM(r.cost)/SUM(r.purchases_14d),2)
            END AS cost_per_order

        FROM sp_targets t

        LEFT JOIN sp_targeting_reports r
            ON t.target_id = r.target_id
            AND r.report_date BETWEEN %s AND %s

        WHERE t.campaign_id = %s

        GROUP BY
            t.target_id,
            t.readable_expression,
            t.bid

        ORDER BY ad_spend DESC
        """

        cursor.execute(query, (start_date, end_date, campaign_id))
        results = cursor.fetchall()

        # Summary
        cursor.execute("""
            SELECT
                COALESCE(SUM(impressions),0) AS impressions,
                COALESCE(SUM(clicks),0) AS clicks,
                COALESCE(SUM(cost),0) AS spend,
                COALESCE(SUM(purchases_14d),0) AS orders
            FROM sp_targeting_reports
            WHERE campaign_id = %s
            AND report_date BETWEEN %s AND %s
        """, (campaign_id, start_date, end_date))

        summary = cursor.fetchone()

        # Trend
        cursor.execute("""
            SELECT
                report_date AS date,
                SUM(impressions) AS impressions,
                SUM(clicks) AS clicks,
                SUM(cost) AS spend,
                SUM(purchases_14d) AS orders
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
        "data": results or [],
        "summary": summary or {},
        "trend": trend or []
    }