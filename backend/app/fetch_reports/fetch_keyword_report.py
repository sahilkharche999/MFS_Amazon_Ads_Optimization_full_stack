import requests
import time
import io
import os
import gzip
import json
import mysql.connector
import logging
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ================= LOGGING SETUP =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("sp_keyword_report_cron")

SCRIPT_START = time.time()
logger.info("========== SP KEYWORD REPORT CRON START ==========")
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
        }
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
start_date = end_date - timedelta(days=14)

logger.info(f"Report Date Range: {start_date} → {end_date}")

payload = {
    "name": f"SP keyword report {start_date} to {end_date}",
    "startDate": start_date.strftime("%Y-%m-%d"),
    "endDate": end_date.strftime("%Y-%m-%d"),
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["targeting"],
        "reportTypeId": "spTargeting",
        "timeUnit": "DAILY",
        "format": "GZIP_JSON",
        "columns": [
            "date", "keywordId", "keyword", "matchType", "campaignId", "campaignName", 
            "adGroupId", "adGroupName", "impressions", "clicks", "cost", "campaignBudgetAmount", 
            "campaignBudgetCurrencyCode", "campaignStatus", "keywordBid", "adKeywordStatus",
            "purchases1d", "purchases7d", "purchases14d", "purchases30d", 
            "sales1d", "sales7d", "sales14d", "sales30d", 
            "unitsSoldClicks1d", "unitsSoldClicks7d", "unitsSoldClicks14d", "unitsSoldClicks30d",
            "attributedSalesSameSku1d", "attributedSalesSameSku7d", "attributedSalesSameSku14d", "attributedSalesSameSku30d",
            "unitsSoldSameSku1d", "unitsSoldSameSku7d", "unitsSoldSameSku14d", "unitsSoldSameSku30d",
            "topOfSearchImpressionShare"
        ]
    }
}

try:
    # ================= STEP 1: GENERATE =================
    logger.info("Requesting keyword report generation")

    resp = requests.post(GENERATE_URL, headers=HEADERS, json=payload)
    resp.raise_for_status()

    report_id = resp.json()["reportId"]
    logger.info(f"Keyword report requested. Report ID: {report_id}")

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
            logger.info("Keyword report generation completed")
            break
        elif status == "FAILED":
            logger.error("Keyword report generation failed")
            raise Exception("Amazon keyword report generation failed")

        time.sleep(POLL_INTERVAL)

    # ================= STEP 3: DOWNLOAD =================
    logger.info("Downloading keyword report file")

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

        logger.info("Starting keyword DB insert process")

        query = """
            INSERT INTO keyword_performance_full (
                date, keywordId, keywordText, matchType, campaignId, campaignName, 
                adGroupId, adGroupName, impressions, clicks, cost, campaignBudget, 
                campaignBudgetCurrencyCode, campaignStatus, keywordBid, adKeywordStatus,
                purchases1d, purchases7d, purchases14d, purchases30d, 
                sales1d, sales7d, sales14d, sales30d, 
                unitsSoldClicks1d, unitsSoldClicks7d, unitsSoldClicks14d, unitsSoldClicks30d,
                attributedSalesSameSku1d, attributedSalesSameSku7d, attributedSalesSameSku14d, attributedSalesSameSku30d,
                unitsSoldSameSku1d, unitsSoldSameSku7d, unitsSoldSameSku14d, unitsSoldSameSku30d,
                topOfSearchImpressionShare
            ) VALUES (
                %(date)s, %(keywordId)s, %(keywordText)s, %(matchType)s, %(campaignId)s, %(campaignName)s, 
                %(adGroupId)s, %(adGroupName)s, %(impressions)s, %(clicks)s, %(cost)s, %(campaignBudget)s, 
                %(campaignBudgetCurrencyCode)s, %(campaignStatus)s, %(keywordBid)s, %(adKeywordStatus)s,
                %(purchases1d)s, %(purchases7d)s, %(purchases14d)s, %(purchases30d)s, 
                %(sales1d)s, %(sales7d)s, %(sales14d)s, %(sales30d)s, 
                %(unitsSoldClicks1d)s, %(unitsSoldClicks7d)s, %(unitsSoldClicks14d)s, %(unitsSoldClicks30d)s,
                %(attributedSalesSameSku1d)s, %(attributedSalesSameSku7d)s, %(attributedSalesSameSku14d)s, %(attributedSalesSameSku30d)s,
                %(unitsSoldSameSku1d)s, %(unitsSoldSameSku7d)s, %(unitsSoldSameSku14d)s, %(unitsSoldSameSku30d)s,
                %(topOfSearchImpressionShare)s
            )
            ON DUPLICATE KEY UPDATE
                keywordText=VALUES(keywordText),
                matchType=VALUES(matchType),
                campaignName=VALUES(campaignName),
                adGroupName=VALUES(adGroupName),
                impressions=VALUES(impressions),
                clicks=VALUES(clicks),
                cost=VALUES(cost),
                campaignBudget=VALUES(campaignBudget),
                campaignBudgetCurrencyCode=VALUES(campaignBudgetCurrencyCode),
                campaignStatus=VALUES(campaignStatus),
                keywordBid=VALUES(keywordBid),
                adKeywordStatus=VALUES(adKeywordStatus),
                purchases1d=VALUES(purchases1d),
                purchases7d=VALUES(purchases7d),
                purchases14d=VALUES(purchases14d),
                purchases30d=VALUES(purchases30d),
                sales1d=VALUES(sales1d),
                sales7d=VALUES(sales7d),
                sales14d=VALUES(sales14d),
                sales30d=VALUES(sales30d),
                unitsSoldClicks1d=VALUES(unitsSoldClicks1d),
                unitsSoldClicks7d=VALUES(unitsSoldClicks7d),
                unitsSoldClicks14d=VALUES(unitsSoldClicks14d),
                unitsSoldClicks30d=VALUES(unitsSoldClicks30d),
                topOfSearchImpressionShare=VALUES(topOfSearchImpressionShare);
        """

        processed = 0

        for row in rows:
            cursor.execute(query, {
                "date": row.get("date"),
                "keywordId": row.get("keywordId"),
                "keywordText": row.get("keyword"), # CORRECTED NAME
                "matchType": row.get("matchType"),
                "campaignId": row.get("campaignId"),
                "campaignName": row.get("campaignName"),
                "adGroupId": row.get("adGroupId"),
                "adGroupName": row.get("adGroupName"),
                "impressions": row.get("impressions", 0),
                "clicks": row.get("clicks", 0),
                "cost": row.get("cost", 0),
                "campaignBudget": row.get("campaignBudgetAmount", 0), # CORRECTED NAME
                "campaignBudgetCurrencyCode": row.get("campaignBudgetCurrencyCode"),
                "campaignStatus": row.get("campaignStatus"),
                "keywordBid": row.get("keywordBid", 0),
                "adKeywordStatus": row.get("adKeywordStatus"),
                "purchases1d": row.get("purchases1d", 0),
                "purchases7d": row.get("purchases7d", 0),
                "purchases14d": row.get("purchases14d", 0),
                "purchases30d": row.get("purchases30d", 0),
                "sales1d": row.get("sales1d", 0),
                "sales7d": row.get("sales7d", 0),
                "sales14d": row.get("sales14d", 0),
                "sales30d": row.get("sales30d", 0),
                "unitsSoldClicks1d": row.get("unitsSoldClicks1d", 0),
                "unitsSoldClicks7d": row.get("unitsSoldClicks7d", 0),
                "unitsSoldClicks14d": row.get("unitsSoldClicks14d", 0),
                "unitsSoldClicks30d": row.get("unitsSoldClicks30d", 0),
                "attributedSalesSameSku1d": row.get("attributedSalesSameSku1d", 0),
                "attributedSalesSameSku7d": row.get("attributedSalesSameSku7d", 0),
                "attributedSalesSameSku14d": row.get("attributedSalesSameSku14d", 0),
                "attributedSalesSameSku30d": row.get("attributedSalesSameSku30d", 0),
                "unitsSoldSameSku1d": row.get("unitsSoldSameSku1d", 0),
                "unitsSoldSameSku7d": row.get("unitsSoldSameSku7d", 0),
                "unitsSoldSameSku14d": row.get("unitsSoldSameSku14d", 0),
                "unitsSoldSameSku30d": row.get("unitsSoldSameSku30d", 0),
                "topOfSearchImpressionShare": row.get("topOfSearchImpressionShare", 0)
            })
            processed += 1

            if processed % 500 == 0:
                logger.info(f"Processed {processed} rows")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"MySQL insert complete. Total rows processed: {processed}")

    store_to_mysql(data)
    

    total_time = round(time.time() - SCRIPT_START, 2)
    logger.info(f"========== KEYWORD CRON SUCCESS (Duration: {total_time}s) ==========")

except Exception as e:
    logger.error("KEYWORD CRON FAILED")
    logger.error(str(e))
    logger.error(traceback.format_exc())
    raise 