import requests
import time
import io
import os
import gzip
import json
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv


print("===== SP TARGET REPORT CRON START =====")
print("Time:", datetime.utcnow().isoformat(), "UTC")

BASE_DIR = os.getcwd()
load_dotenv(".env")

# ==============================
# AMAZON AUTH
# ==============================

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
    return {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": os.getenv("AMAZON_CLIENT_ID"),
        "Amazon-Advertising-API-Scope": os.getenv("AMAZON_PROFILE_ID"),
        "Content-Type": "application/json"
    }


# ==============================
# DATE RANGE (Last 14 Days)
# ==============================

end_date = datetime.utcnow().date() - timedelta(days=1)
start_date = end_date - timedelta(days=14)

print(f"Fetching data from {start_date} to {end_date}")

# ==============================
# REPORT PAYLOAD
# ==============================

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


# ==============================
# STEP 1: GENERATE REPORT
# ==============================

print("Requesting report...")
response = requests.post(GENERATE_URL, headers=HEADERS, json=payload)
response.raise_for_status()
report_id = response.json()["reportId"]

print("Report ID:", report_id)

# ==============================
# STEP 2: POLL STATUS
# ==============================

status_url = STATUS_URL_TEMPLATE.format(report_id)
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

    time.sleep(10)


# ==============================
# STEP 3: DOWNLOAD + DECOMPRESS
# ==============================

print("Downloading report...")

file_resp = requests.get(download_url)
file_resp.raise_for_status()

with gzip.GzipFile(fileobj=io.BytesIO(file_resp.content)) as gz:
    data = json.load(gz)

print("Rows downloaded:", len(data))


# ==============================
# STEP 4: STORE TO MYSQL
# ==============================

def store_sp_targets(rows):

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )

    cursor = conn.cursor()

    query = """
    INSERT INTO sp_targeting_reports (
        campaign_id,
        campaign_name,
        campaign_status,
        ad_group_id,
        ad_group_name,
        target_id,
        targeting,
        keyword_type,
        match_type,
        report_date,
        impressions,
        clicks,
        cost,
        sales_7d,
        sales_14d,
        sales_30d,
        purchases_7d,
        purchases_14d,
        purchases_30d,
        units_sold_7d,
        units_sold_14d,
        units_sold_30d,
        keyword_bid
    )
    VALUES (
        %(campaign_id)s,
        %(campaign_name)s,
        %(campaign_status)s,
        %(ad_group_id)s,
        %(ad_group_name)s,
        %(target_id)s,
        %(targeting)s,
        %(keyword_type)s,
        %(match_type)s,
        %(report_date)s,
        %(impressions)s,
        %(clicks)s,
        %(cost)s,
        %(sales_7d)s,
        %(sales_14d)s,
        %(sales_30d)s,
        %(purchases_7d)s,
        %(purchases_14d)s,
        %(purchases_30d)s,
        %(units_sold_7d)s,
        %(units_sold_14d)s,
        %(units_sold_30d)s,
        %(keyword_bid)s
    )
    ON DUPLICATE KEY UPDATE
        impressions = VALUES(impressions),
        clicks = VALUES(clicks),
        cost = VALUES(cost),
        sales_7d = VALUES(sales_7d),
        sales_14d = VALUES(sales_14d),
        sales_30d = VALUES(sales_30d),
        purchases_7d = VALUES(purchases_7d),
        purchases_14d = VALUES(purchases_14d),
        purchases_30d = VALUES(purchases_30d),
        units_sold_7d = VALUES(units_sold_7d),
        units_sold_14d = VALUES(units_sold_14d),
        units_sold_30d = VALUES(units_sold_30d),
        keyword_bid = VALUES(keyword_bid),
        campaign_status = VALUES(campaign_status)
    """

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

    cursor.executemany(query, insert_data)

    conn.commit()
    cursor.close()
    conn.close()


store_sp_targets(data)

print("Data stored successfully")
print("===== SP TARGET REPORT CRON SUCCESS =====")