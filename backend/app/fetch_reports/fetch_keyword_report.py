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
POLL_INTERVAL = 10

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
        "groupBy": ["adGroup"],
        "reportTypeId": "spKeywords",
        "timeUnit": "DAILY",
        "format": "GZIP_JSON",
        "columns": [ ... ]  # keep your full column list unchanged
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

        query = """YOUR ORIGINAL INSERT QUERY UNCHANGED"""

        processed = 0

        for row in rows:
            cursor.execute(query, row)
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