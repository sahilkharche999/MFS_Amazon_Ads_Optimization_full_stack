import requests
import time
import io
import os
import gzip
import json
import mysql.connector
from decimal import Decimal
from datetime import datetime, timedelta
from dotenv import load_dotenv

print("===== CRON JOB START =====")
print("Time:", datetime.utcnow().isoformat(), "UTC")

BASE_DIR = os.getcwd()

load_dotenv(".env")
print("AMAZON_CLIENT_ID:", os.getenv("AMAZON_CLIENT_ID"))

# venv_path = "/Users/consultadd/Desktop/MFS-Amazon-ads-optimization1/MFS_Amazon_Ads_optimization/venv/bin/python3"

# ================= CONFIG =================

def get_access_token():
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
    return r.json()["access_token"]


def get_headers():
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": os.getenv("AMAZON_CLIENT_ID"),
        "Amazon-Advertising-API-Scope": os.getenv("AMAZON_PROFILE_ID"),
        "Content-Type": "application/json"
    }
    return headers


GENERATE_URL = "https://advertising-api.amazon.com/reporting/reports"
STATUS_URL_TEMPLATE = "https://advertising-api.amazon.com/reporting/reports/{report_id}"

REPORTS_DIR = "reports"
POLL_INTERVAL = 10  # seconds

HEADERS = get_headers()

# ================ DATE RANGE ================

end_date = datetime.utcnow().date() - timedelta(days=1)
start_date = end_date - timedelta(days=14)

report_name = f"SP campaign report {start_date} to {end_date}"

# ================ PAYLOAD ===================

payload = {
    "name": report_name,
    "startDate": start_date.strftime("%Y-%m-%d"),
    "endDate": end_date.strftime("%Y-%m-%d"),
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["Campaign"],
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
            "costPerClick",
            "clickThroughRate",

            "sales1d",
            "sales7d",
            "sales14d",
            "sales30d",

            "purchases1d",
            "purchases7d",
            "purchases14d",
            "purchases30d",

            "unitsSoldSameSku1d",
            "unitsSoldSameSku7d",
            "unitsSoldSameSku14d",
            "unitsSoldSameSku30d"
        ]
    }
}

# ================ STEP 1: GENERATE REPORT ================

print("Requesting report...")

resp = requests.post(GENERATE_URL, headers=HEADERS, json=payload)
resp.raise_for_status()
report_id = resp.json()["reportId"]

print("Report ID:", report_id)
print("Report requested:", report_id)

# ================ STEP 2: POLL STATUS ====================

status_url = STATUS_URL_TEMPLATE.format(report_id=report_id)

download_url = None

while True:
    status_resp = requests.get(status_url, headers=HEADERS)
    status_resp.raise_for_status()

    status_data = status_resp.json()
    status = status_data["status"]

    print("Status:", status)

    if status == "COMPLETED":
        download_url = status_data["url"]
        break
    elif status == "FAILED":
        raise Exception("Report generation failed")

    time.sleep(POLL_INTERVAL)

# ================ STEP 3: DOWNLOAD ========================

os.makedirs(REPORTS_DIR, exist_ok=True)

file_name = f"sp_keywords_{start_date}_to_{end_date}.json"
json_path = os.path.join(REPORTS_DIR, file_name)

print("Downloading report file...")
file_resp = requests.get(download_url)
file_resp.raise_for_status()

# Decompress in-memory and write JSON
with gzip.GzipFile(fileobj=io.BytesIO(file_resp.content)) as gz:
    data = json.load(gz)

print("Rows downloaded:", len(data))


# ================ STEP 4: STORE IN MYSQL ====================

def store_to_mysql(rows):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )
    cursor = conn.cursor()

    query = """
    INSERT INTO campaign_performance_daily (
        date,
        campaignId,
        campaignName,
        campaignStatus,
        campaignBudgetAmount,
        campaignBudgetType,
        campaignBudgetCurrencyCode,
        impressions,
        clicks,
        cost,
        spend,
        purchases1d,
        purchases7d,
        purchases14d,
        purchases30d,
        sales1d,
        sales7d,
        sales14d,
        sales30d,
        unitsSoldSameSku1d,
        unitsSoldSameSku7d,
        unitsSoldSameSku14d,
        unitsSoldSameSku30d,
        costPerClick,
        clickThroughRate
    )
    VALUES (
        %(date)s,
        %(campaignId)s,
        %(campaignName)s,
        %(campaignStatus)s,
        %(campaignBudgetAmount)s,
        %(campaignBudgetType)s,
        %(campaignBudgetCurrencyCode)s,
        %(impressions)s,
        %(clicks)s,
        %(cost)s,
        %(spend)s,
        %(purchases1d)s,
        %(purchases7d)s,
        %(purchases14d)s,
        %(purchases30d)s,
        %(sales1d)s,
        %(sales7d)s,
        %(sales14d)s,
        %(sales30d)s,
        %(unitsSoldSameSku1d)s,
        %(unitsSoldSameSku7d)s,
        %(unitsSoldSameSku14d)s,
        %(unitsSoldSameSku30d)s,
        %(costPerClick)s,
        %(clickThroughRate)s
    )
    ON DUPLICATE KEY UPDATE
        impressions = VALUES(impressions),
        clicks = VALUES(clicks),
        cost = VALUES(cost),
        spend = VALUES(spend),
        purchases7d = VALUES(purchases7d),
        purchases14d = VALUES(purchases14d),
        purchases30d = VALUES(purchases30d),
        sales7d = VALUES(sales7d),
        sales14d = VALUES(sales14d),
        sales30d = VALUES(sales30d),
        unitsSoldSameSku7d = VALUES(unitsSoldSameSku7d),
        unitsSoldSameSku14d = VALUES(unitsSoldSameSku14d),
        unitsSoldSameSku30d = VALUES(unitsSoldSameSku30d),
        campaignStatus = VALUES(campaignStatus),
        costPerClick = VALUES(costPerClick),
        clickThroughRate = VALUES(clickThroughRate)
    """

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
    conn.commit()
    cursor.close()
    conn.close()

store_to_mysql(data)
print("Data stored in database successfully")


print("===== CRON JOB SUCCESS =====")

