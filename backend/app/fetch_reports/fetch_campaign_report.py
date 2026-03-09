import gzip
import io
import json
import logging
import os
import time
import traceback
from datetime import datetime, timedelta

import mysql.connector
import requests
from dotenv import load_dotenv

# ================= LOGGING SETUP =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("sp_campaign_report_cron")

SCRIPT_START = time.time()
logger.info("========== SP CAMPAIGN REPORT CRON START ==========")
logger.info(f"UTC Time: {datetime.utcnow().isoformat()}")

load_dotenv("../../../.env")


# ================= CONFIG =================

def get_access_token():
    logger.info("Requesting Amazon access token")
    r = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": os.getenv("AMAZON_REFRESH_TOKEN"),
            "client_id": os.getenv("AMAZON_CLIENT_ID"),
            "client_secret": os.getenv("AMAZON_CLIENT_SECRET")
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    r.raise_for_status()
    logger.info("Access token retrieved successfully")
    return r.json()["access_token"]


def get_headers():
    token = get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Amazon-Advertising-API-ClientId": os.getenv("AMAZON_CLIENT_ID"),
        "Amazon-Advertising-API-Scope": os.getenv("AMAZON_PROFILE_ID"),
        "Content-Type": "application/json"
    }


GENERATE_URL = "https://advertising-api.amazon.com/reporting/reports"
STATUS_URL_TEMPLATE = "https://advertising-api.amazon.com/reporting/reports/{report_id}"
POLL_INTERVAL = 45

HEADERS = get_headers()

# ================= DATE RANGE =================
end_date = datetime.utcnow().date() - timedelta(days=1)
start_date = end_date - timedelta(days=30)

logger.info(f"Report Date Range: {start_date} → {end_date}")

payload = {
    "name": f"SP campaign report {start_date} to {end_date}",
    "startDate": start_date.strftime("%Y-%m-%d"),
    "endDate": end_date.strftime("%Y-%m-%d"),
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["campaign"],
        "reportTypeId": "spCampaigns",
        "timeUnit": "DAILY",
        "format": "GZIP_JSON",
        "columns": [
            "date",
            "campaignId",
            "campaignName",
            "campaignStatus",
            "campaignBudgetAmount",
            "campaignBudgetType",
            "campaignBudgetCurrencyCode",
            "impressions",
            "clicks",
            "cost",
            "spend",
            "purchases1d",
            "purchases7d",
            "purchases14d",
            "purchases30d",
            "sales1d",
            "sales7d",
            "sales14d",
            "sales30d",
            "unitsSoldSameSku1d",
            "unitsSoldSameSku7d",
            "unitsSoldSameSku14d",
            "unitsSoldSameSku30d",
            "costPerClick",
            "clickThroughRate"
        ]
    }
}

try:
    # ================= STEP 1: GENERATE =================
    logger.info("Requesting report generation from Amazon")

    resp = requests.post(GENERATE_URL, headers=HEADERS, json=payload)
    resp.raise_for_status()

    report_id = resp.json()["reportId"]
    logger.info(f"Report generated. Report ID: {report_id}")

    # ================= STEP 2: POLL =================
    status_url = STATUS_URL_TEMPLATE.format(report_id=report_id)
    download_url = None

    logger.info("Polling report status")

    while True:
        status_resp = requests.get(status_url, headers=HEADERS)
        status_resp.raise_for_status()

        status_data = status_resp.json()
        status = status_data["status"]

        logger.info(f"Current report status: {status}")

        if status == "COMPLETED":
            download_url = status_data["url"]
            logger.info("Report generation completed")
            break
        elif status == "FAILED":
            logger.error("Report generation failed")
            raise Exception("Amazon report generation failed")

        time.sleep(POLL_INTERVAL)

    # ================= STEP 3: DOWNLOAD =================
    logger.info("Downloading report file")

    file_resp = requests.get(download_url)
    file_resp.raise_for_status()

    with gzip.GzipFile(fileobj=io.BytesIO(file_resp.content)) as gz:
        data = json.load(gz)

    logger.info(f"Rows downloaded: {len(data)}")


    # ================= STEP 4: STORE IN MYSQL =================
    def store_to_mysql(rows):
        logger.info("Opening MySQL connection")

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )

        cursor = conn.cursor()
        logger.info("Starting DB insert process")

        query = """
            INSERT INTO campaign_performance_daily (
                date, campaignId, campaignName, campaignStatus, campaignBudgetAmount,
                campaignBudgetType, campaignBudgetCurrencyCode, impressions, clicks, cost,
                spend, purchases1d, purchases7d, purchases14d, purchases30d,
                sales1d, sales7d, sales14d, sales30d, unitsSoldSameSku1d,
                unitsSoldSameSku7d, unitsSoldSameSku14d, unitsSoldSameSku30d,
                costPerClick, clickThroughRate
            ) VALUES (
                %(date)s, %(campaignId)s, %(campaignName)s, %(campaignStatus)s, %(campaignBudgetAmount)s,
                %(campaignBudgetType)s, %(campaignBudgetCurrencyCode)s, %(impressions)s, %(clicks)s, %(cost)s,
                %(spend)s, %(purchases1d)s, %(purchases7d)s, %(purchases14d)s, %(purchases30d)s,
                %(sales1d)s, %(sales7d)s, %(sales14d)s, %(sales30d)s, %(unitsSoldSameSku1d)s,
                %(unitsSoldSameSku7d)s, %(unitsSoldSameSku14d)s, %(unitsSoldSameSku30d)s,
                %(costPerClick)s, %(clickThroughRate)s
            )
            ON DUPLICATE KEY UPDATE
                campaignName=VALUES(campaignName),
                campaignStatus=VALUES(campaignStatus),
                campaignBudgetAmount=VALUES(campaignBudgetAmount),
                campaignBudgetType=VALUES(campaignBudgetType),
                campaignBudgetCurrencyCode=VALUES(campaignBudgetCurrencyCode),
                impressions=VALUES(impressions),
                clicks=VALUES(clicks),
                cost=VALUES(cost),
                spend=VALUES(spend),
                purchases1d=VALUES(purchases1d),
                purchases7d=VALUES(purchases7d),
                purchases14d=VALUES(purchases14d),
                purchases30d=VALUES(purchases30d),
                sales1d=VALUES(sales1d),
                sales7d=VALUES(sales7d),
                sales14d=VALUES(sales14d),
                sales30d=VALUES(sales30d),
                unitsSoldSameSku1d=VALUES(unitsSoldSameSku1d),
                unitsSoldSameSku7d=VALUES(unitsSoldSameSku7d),
                unitsSoldSameSku14d=VALUES(unitsSoldSameSku14d),
                unitsSoldSameSku30d=VALUES(unitsSoldSameSku30d),
                costPerClick=VALUES(costPerClick),
                clickThroughRate=VALUES(clickThroughRate);
        """

        inserted = 0

        for row in rows:
            cursor.execute(query, {
                "date": row.get("date"),
                "campaignId": row.get("campaignId"),
                "campaignName": row.get("campaignName"),
                "campaignStatus": row.get("campaignStatus"),
                "campaignBudgetAmount": row.get("campaignBudgetAmount", 0),
                "campaignBudgetType": row.get("campaignBudgetType"),
                "campaignBudgetCurrencyCode": row.get("campaignBudgetCurrencyCode"),
                "impressions": row.get("impressions", 0),
                "clicks": row.get("clicks", 0),
                "cost": row.get("cost", 0),
                "spend": row.get("spend", 0),
                "purchases1d": row.get("purchases1d", 0),
                "purchases7d": row.get("purchases7d", 0),
                "purchases14d": row.get("purchases14d", 0),
                "purchases30d": row.get("purchases30d", 0),
                "sales1d": row.get("sales1d", 0),
                "sales7d": row.get("sales7d", 0),
                "sales14d": row.get("sales14d", 0),
                "sales30d": row.get("sales30d", 0),
                "unitsSoldSameSku1d": row.get("unitsSoldSameSku1d", 0),
                "unitsSoldSameSku7d": row.get("unitsSoldSameSku7d", 0),
                "unitsSoldSameSku14d": row.get("unitsSoldSameSku14d", 0),
                "unitsSoldSameSku30d": row.get("unitsSoldSameSku30d", 0),
                "costPerClick": row.get("costPerClick", 0),
                "clickThroughRate": row.get("clickThroughRate", 0),
            })
            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"DB insert completed. Rows processed: {inserted}")


    store_to_mysql(data)

    total_time = round(time.time() - SCRIPT_START, 2)
    logger.info(f"========== CRON JOB SUCCESS (Duration: {total_time}s) ==========")

except Exception as e:
    logger.error("CRON JOB FAILED")
    logger.error(str(e))
    logger.error(traceback.format_exc())
    raise
