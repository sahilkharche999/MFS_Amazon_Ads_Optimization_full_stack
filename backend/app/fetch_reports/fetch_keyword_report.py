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

report_name = f"SP keyword report {start_date} to {end_date}"

# ================ PAYLOAD ===================

payload = {
    "name": report_name,
    "startDate": start_date.strftime("%Y-%m-%d"),
    "endDate": end_date.strftime("%Y-%m-%d"),
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["adGroup"],
        "reportTypeId": "spKeywords",
        "timeUnit": "DAILY",
        "format": "GZIP_JSON",
        "columns": [
            "attributedSalesSameSku1d",
            "attributedUnitsOrdered1dSameSKU",
            "date",
            "attributedSales30d",
            "attributedUnitsOrdered30d",
            "attributedSales1d",
            "unitsSoldClicks1d",
            "matchType",
            "attributedSales1dSameSKU",
            "attributedSalesSameSku14d",
            "sales7d",
            "attributedConversions7d",
            "attributedSalesSameSku30d",
            "kindleEditionNormalizedPagesRoyalties14d",
            "unitsSoldSameSku1d",
            "attributedKindleEditionNormalizedPagesRead14d",
            "attributedConversions7dSameSKU",
            "attributedUnitsOrdered7dSameSKU",
            "keyword",
            "purchasesSameSku7d",
            "purchases7d",
            "attributedConversions1dSameSKU",
            "unitsSoldSameSku30d",
            "unitsSoldClicks14d",
            "attributedUnitsOrdered7d",
            "attributedSales14dSameSKU",
            "kindleEditionNormalizedPagesRead14d",
            "unitsSoldClicks30d",
            "keywordText",
            "attributedConversions30dSameSKU",
            "campaignBudgetCurrencyCode",
            "attributedUnitsOrdered14dSameSKU",
            "unitsSoldClicks7d",
            "unitsSoldSameSku14d",
            "keywordId",
            "attributedSales7d",
            "attributedConversions1d",
            "attributedSalesSameSku7d",
            "topOfSearchImpressionShare",
            "attributedConversions30d",
            "sales1d",
            "purchasesSameSku14d",
            "attributedConversions14d",
            "purchasesSameSku1d",
            "purchases1d",
            "currency",
            "unitsSoldSameSku7d",
            "cost",
            "attributedKindleEditionNormalizedPagesRoyalties14d",
            "attributedSales7dSameSKU",
            "sales14d",
            "sales30d",
            "attributedSales30dSameSKU",
            "impressions",
            "purchasesSameSku30d",
            "purchases14d",
            "attributedUnitsOrdered1d",
            "purchases30d",
            "attributedConversions14dSameSKU",
            "clicks",
            "attributedSales14d",
            "attributedUnitsOrdered30dSameSKU",
            "attributedUnitsOrdered14d",
            "keywordBid",
            "campaignBudget",
            "adGroupName",
            "campaignId",
            "campaignBudgetType",
            "adKeywordStatus",
            "campaignStatus",
            "campaignName",
            "campaignBudgetAmount",
            "adGroupId"
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
    INSERT INTO keyword_performance_full (
        date,
        attributedSalesSameSku1d,
        attributedUnitsOrdered1dSameSKU,
        attributedSales30d,
        attributedUnitsOrdered30d,
        attributedSales1d,
        unitsSoldClicks1d,
        matchType,
        attributedSales1dSameSKU,
        attributedSalesSameSku14d,
        sales7d,
        attributedConversions7d,
        attributedSalesSameSku30d,
        kindleEditionNormalizedPagesRoyalties14d,
        unitsSoldSameSku1d,
        attributedKindleEditionNormalizedPagesRead14d,
        attributedConversions7dSameSKU,
        attributedUnitsOrdered7dSameSKU,
        keyword,
        purchasesSameSku7d,
        purchases7d,
        attributedConversions1dSameSKU,
        unitsSoldSameSku30d,
        unitsSoldClicks14d,
        attributedUnitsOrdered7d,
        attributedSales14dSameSKU,
        kindleEditionNormalizedPagesRead14d,
        unitsSoldClicks30d,
        keywordText,
        attributedConversions30dSameSKU,
        campaignBudgetCurrencyCode,
        attributedUnitsOrdered14dSameSKU,
        unitsSoldClicks7d,
        unitsSoldSameSku14d,
        keywordId,
        attributedSales7d,
        attributedConversions1d,
        attributedSalesSameSku7d,
        topOfSearchImpressionShare,
        attributedConversions30d,
        sales1d,
        purchasesSameSku14d,
        attributedConversions14d,
        purchasesSameSku1d,
        purchases1d,
        currency,
        unitsSoldSameSku7d,
        cost,
        attributedKindleEditionNormalizedPagesRoyalties14d,
        attributedSales7dSameSKU,
        sales14d,
        sales30d,
        attributedSales30dSameSKU,
        impressions,
        purchasesSameSku30d,
        purchases14d,
        attributedUnitsOrdered1d,
        purchases30d,
        attributedConversions14dSameSKU,
        clicks,
        attributedSales14d,
        attributedUnitsOrdered30dSameSKU,
        attributedUnitsOrdered14d,
        keywordBid,
        campaignBudget,
        adGroupName,
        campaignId,
        campaignBudgetType,
        adKeywordStatus,
        campaignStatus,
        campaignName,
        campaignBudgetAmount,
        adGroupId
    )
    VALUES (
        %(date)s,
        %(attributedSalesSameSku1d)s,
        %(attributedUnitsOrdered1dSameSKU)s,
        %(attributedSales30d)s,
        %(attributedUnitsOrdered30d)s,
        %(attributedSales1d)s,
        %(unitsSoldClicks1d)s,
        %(matchType)s,
        %(attributedSales1dSameSKU)s,
        %(attributedSalesSameSku14d)s,
        %(sales7d)s,
        %(attributedConversions7d)s,
        %(attributedSalesSameSku30d)s,
        %(kindleEditionNormalizedPagesRoyalties14d)s,
        %(unitsSoldSameSku1d)s,
        %(attributedKindleEditionNormalizedPagesRead14d)s,
        %(attributedConversions7dSameSKU)s,
        %(attributedUnitsOrdered7dSameSKU)s,
        %(keyword)s,
        %(purchasesSameSku7d)s,
        %(purchases7d)s,
        %(attributedConversions1dSameSKU)s,
        %(unitsSoldSameSku30d)s,
        %(unitsSoldClicks14d)s,
        %(attributedUnitsOrdered7d)s,
        %(attributedSales14dSameSKU)s,
        %(kindleEditionNormalizedPagesRead14d)s,
        %(unitsSoldClicks30d)s,
        %(keywordText)s,
        %(attributedConversions30dSameSKU)s,
        %(campaignBudgetCurrencyCode)s,
        %(attributedUnitsOrdered14dSameSKU)s,
        %(unitsSoldClicks7d)s,
        %(unitsSoldSameSku14d)s,
        %(keywordId)s,
        %(attributedSales7d)s,
        %(attributedConversions1d)s,
        %(attributedSalesSameSku7d)s,
        %(topOfSearchImpressionShare)s,
        %(attributedConversions30d)s,
        %(sales1d)s,
        %(purchasesSameSku14d)s,
        %(attributedConversions14d)s,
        %(purchasesSameSku1d)s,
        %(purchases1d)s,
        %(currency)s,
        %(unitsSoldSameSku7d)s,
        %(cost)s,
        %(attributedKindleEditionNormalizedPagesRoyalties14d)s,
        %(attributedSales7dSameSKU)s,
        %(sales14d)s,
        %(sales30d)s,
        %(attributedSales30dSameSKU)s,
        %(impressions)s,
        %(purchasesSameSku30d)s,
        %(purchases14d)s,
        %(attributedUnitsOrdered1d)s,
        %(purchases30d)s,
        %(attributedConversions14dSameSKU)s,
        %(clicks)s,
        %(attributedSales14d)s,
        %(attributedUnitsOrdered30dSameSKU)s,
        %(attributedUnitsOrdered14d)s,
        %(keywordBid)s,
        %(campaignBudget)s,
        %(adGroupName)s,
        %(campaignId)s,
        %(campaignBudgetType)s,
        %(adKeywordStatus)s,
        %(campaignStatus)s,
        %(campaignName)s,
        %(campaignBudgetAmount)s,
        %(adGroupId)s
    )
    ON DUPLICATE KEY UPDATE
        impressions = VALUES(impressions),
        clicks = VALUES(clicks),
        cost = VALUES(cost),
        sales1d = VALUES(sales1d),
        sales7d = VALUES(sales7d),
        sales14d = VALUES(sales14d),
        sales30d = VALUES(sales30d),
        purchases1d = VALUES(purchases1d),
        purchases7d = VALUES(purchases7d),
        purchases14d = VALUES(purchases14d),
        purchases30d = VALUES(purchases30d),
        keywordBid = VALUES(keywordBid),
        campaignStatus = VALUES(campaignStatus)
    """

    for row in rows:
        cursor.execute(query, {
            "date": row["date"],
            "attributedSalesSameSku1d": row.get("attributedSalesSameSku1d", 0),
            "attributedUnitsOrdered1dSameSKU": row.get("attributedUnitsOrdered1dSameSKU", 0),
            "attributedSales30d": row.get("attributedSales30d", 0),
            "attributedUnitsOrdered30d": row.get("attributedUnitsOrdered30d", 0),
            "attributedSales1d": row.get("attributedSales1d", 0),
            "unitsSoldClicks1d": row.get("unitsSoldClicks1d", 0),
            "matchType": row.get("matchType"),
            "attributedSales1dSameSKU": row.get("attributedSales1dSameSKU", 0),
            "attributedSalesSameSku14d": row.get("attributedSalesSameSku14d", 0),
            "sales7d": row.get("sales7d", 0),
            "attributedConversions7d": row.get("attributedConversions7d", 0),
            "attributedSalesSameSku30d": row.get("attributedSalesSameSku30d", 0),
            "kindleEditionNormalizedPagesRoyalties14d": row.get("kindleEditionNormalizedPagesRoyalties14d", 0),
            "unitsSoldSameSku1d": row.get("unitsSoldSameSku1d", 0),
            "attributedKindleEditionNormalizedPagesRead14d": row.get("attributedKindleEditionNormalizedPagesRead14d", 0),
            "attributedConversions7dSameSKU": row.get("attributedConversions7dSameSKU", 0),
            "attributedUnitsOrdered7dSameSKU": row.get("attributedUnitsOrdered7dSameSKU", 0),
            "keyword": row.get("keyword"),
            "purchasesSameSku7d": row.get("purchasesSameSku7d", 0),
            "purchases7d": row.get("purchases7d", 0),
            "attributedConversions1dSameSKU": row.get("attributedConversions1dSameSKU", 0),
            "unitsSoldSameSku30d": row.get("unitsSoldSameSku30d", 0),
            "unitsSoldClicks14d": row.get("unitsSoldClicks14d", 0),
            "attributedUnitsOrdered7d": row.get("attributedUnitsOrdered7d", 0),
            "attributedSales14dSameSKU": row.get("attributedSales14dSameSKU", 0),
            "kindleEditionNormalizedPagesRead14d": row.get("kindleEditionNormalizedPagesRead14d", 0),
            "unitsSoldClicks30d": row.get("unitsSoldClicks30d", 0),
            "keywordText": row.get("keywordText"),
            "attributedConversions30dSameSKU": row.get("attributedConversions30dSameSKU", 0),
            "campaignBudgetCurrencyCode": row.get("campaignBudgetCurrencyCode"),
            "attributedUnitsOrdered14dSameSKU": row.get("attributedUnitsOrdered14dSameSKU", 0),
            "unitsSoldClicks7d": row.get("unitsSoldClicks7d", 0),
            "unitsSoldSameSku14d": row.get("unitsSoldSameSku14d", 0),
            "keywordId": row.get("keywordId"),
            "attributedSales7d": row.get("attributedSales7d", 0),
            "attributedConversions1d": row.get("attributedConversions1d", 0),
            "attributedSalesSameSku7d": row.get("attributedSalesSameSku7d", 0),
            "topOfSearchImpressionShare": row.get("topOfSearchImpressionShare"),
            "attributedConversions30d": row.get("attributedConversions30d", 0),
            "sales1d": row.get("sales1d", 0),
            "purchasesSameSku14d": row.get("purchasesSameSku14d", 0),
            "attributedConversions14d": row.get("attributedConversions14d", 0),
            "purchasesSameSku1d": row.get("purchasesSameSku1d", 0),
            "purchases1d": row.get("purchases1d", 0),
            "currency": row.get("currency"),
            "unitsSoldSameSku7d": row.get("unitsSoldSameSku7d", 0),
            "cost": row.get("cost", 0),
            "attributedKindleEditionNormalizedPagesRoyalties14d": row.get("attributedKindleEditionNormalizedPagesRoyalties14d", 0),
            "attributedSales7dSameSKU": row.get("attributedSales7dSameSKU", 0),
            "sales14d": row.get("sales14d", 0),
            "sales30d": row.get("sales30d", 0),
            "attributedSales30dSameSKU": row.get("attributedSales30dSameSKU", 0),
            "impressions": row.get("impressions", 0),
            "purchasesSameSku30d": row.get("purchasesSameSku30d", 0),
            "purchases14d": row.get("purchases14d", 0),
            "attributedUnitsOrdered1d": row.get("attributedUnitsOrdered1d", 0),
            "purchases30d": row.get("purchases30d", 0),
            "attributedConversions14dSameSKU": row.get("attributedConversions14dSameSKU", 0),
            "clicks": row.get("clicks", 0),
            "attributedSales14d": row.get("attributedSales14d", 0),
            "attributedUnitsOrdered30dSameSKU": row.get("attributedUnitsOrdered30dSameSKU", 0),
            "attributedUnitsOrdered14d": row.get("attributedUnitsOrdered14d", 0),
            "keywordBid": row.get("keywordBid", 0),
            "campaignBudget": row.get("campaignBudget"),
            "adGroupName": row.get("adGroupName"),
            "campaignId": row.get("campaignId"),
            "campaignBudgetType": row.get("campaignBudgetType"),
            "adKeywordStatus": row.get("adKeywordStatus"),
            "campaignStatus": row.get("campaignStatus"),
            "campaignName": row.get("campaignName"),
            "campaignBudgetAmount": row.get("campaignBudgetAmount"),
            "adGroupId": row.get("adGroupId"),
        })

    conn.commit()
    cursor.close()
    conn.close()

store_to_mysql(data)
print("Data stored in database successfully")


print("===== CRON JOB SUCCESS =====")

