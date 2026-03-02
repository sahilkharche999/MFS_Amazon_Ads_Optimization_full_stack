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
logger = logging.getLogger("sp_target_report_cron")

SCRIPT_START = time.time()
logger.info("========== SP TARGET REPORT CRON START ==========")
logger.info(f"UTC Time: {datetime.utcnow().isoformat()}")

load_dotenv("../../../.env")

# ================= AMAZON AUTH =================

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


# ================= DATE RANGE =================

end_date = datetime.utcnow().date() - timedelta(days=1)
start_date = end_date - timedelta(days=14)

logger.info(f"Report Date Range: {start_date} → {end_date}")

# ================= REPORT PAYLOAD =================

payload = {
    "name": f"SP Targets Report {start_date} to {end_date}",
    "startDate": start_date.strftime("%Y-%m-%d"),
    "endDate": end_date.strftime("%Y-%m-%d"),
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["targeting"],
        "reportTypeId": "spTargets",
        "timeUnit": "DAILY",
        "format": "GZIP_JSON",
        "columns": [
            "date",
            "campaignId",
            "campaignName",
            "campaignStatus",
            "adGroupId",
            "adGroupName",
            "keywordId",
            "targeting",
            "keywordType",
            "matchType",
            "keywordBid",
            "impressions",
            "clicks",
            "cost",
            "sales7d",
            "sales14d",
            "sales30d",
            "purchases7d",
            "purchases14d",
            "purchases30d",
            "unitsSoldClicks7d",
            "unitsSoldClicks14d",
            "unitsSoldClicks30d"
        ]
    }
}

GENERATE_URL = "https://advertising-api.amazon.com/reporting/reports"
STATUS_URL_TEMPLATE = "https://advertising-api.amazon.com/reporting/reports/{}"
HEADERS = get_headers()

try:
    # ================= STEP 1: GENERATE =================
    logger.info("Requesting target report generation")

    response = requests.post(GENERATE_URL, headers=HEADERS, json=payload)
    response.raise_for_status()

    report_id = response.json()["reportId"]
    logger.info(f"Target report requested. Report ID: {report_id}")

    # ================= STEP 2: POLL =================
    status_url = STATUS_URL_TEMPLATE.format(report_id)
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
            logger.info("Target report generation completed")
            break
        elif status == "FAILED":
            logger.error("Target report generation failed")
            raise Exception("Amazon target report generation failed")

        time.sleep(10)

    # ================= STEP 3: DOWNLOAD =================
    logger.info("Downloading target report")

    file_resp = requests.get(download_url)
    file_resp.raise_for_status()

    with gzip.GzipFile(fileobj=io.BytesIO(file_resp.content)) as gz:
        data = json.load(gz)

    logger.info(f"Rows downloaded: {len(data)}")

    # ================= STEP 4: STORE IN MYSQL =================

    def store_sp_targets(rows):
        logger.info("Opening MySQL connection")

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )

        cursor = conn.cursor()

        query = """YOUR ORIGINAL INSERT QUERY UNCHANGED"""

        insert_data = []

        for row in rows:
            insert_data.append({
                "campaign_id": row.get("campaignId"),
                "campaign_name": row.get("campaignName"),
                "campaign_status": row.get("campaignStatus"),
                "ad_group_id": row.get("adGroupId"),
                "ad_group_name": row.get("adGroupName"),
                "target_id": row.get("keywordId"),
                "targeting": row.get("targeting"),
                "keyword_type": row.get("keywordType"),
                "match_type": row.get("matchType"),
                "report_date": row.get("date"),
                "impressions": row.get("impressions", 0),
                "clicks": row.get("clicks", 0),
                "cost": row.get("cost", 0),
                "sales_7d": row.get("sales7d", 0),
                "sales_14d": row.get("sales14d", 0),
                "sales_30d": row.get("sales30d", 0),
                "purchases_7d": row.get("purchases7d", 0),
                "purchases_14d": row.get("purchases14d", 0),
                "purchases_30d": row.get("purchases30d", 0),
                "units_sold_7d": row.get("unitsSoldClicks7d", 0),
                "units_sold_14d": row.get("unitsSoldClicks14d", 0),
                "units_sold_30d": row.get("unitsSoldClicks30d", 0),
                "keyword_bid": row.get("keywordBid", 0),
            })

        logger.info(f"Preparing to insert {len(insert_data)} rows into MySQL")

        cursor.executemany(query, insert_data)

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("MySQL insert completed successfully")

    store_sp_targets(data)

    total_time = round(time.time() - SCRIPT_START, 2)
    logger.info(f"========== TARGET CRON SUCCESS (Duration: {total_time}s) ==========")

except Exception as e:
    logger.error("TARGET CRON FAILED")
    logger.error(str(e))
    logger.error(traceback.format_exc())
    raise