from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
import os, json, time, traceback, logging, re
import asyncio
import pymysql
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor  # ← ADDED

from app.database.database import get_connection

load_dotenv()

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("optimize_campaign")

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

SYSTEM_PROMPT = """
You are an Amazon Sponsored Products optimization strategist for book publishing.

GOAL: Maximize profitable scale, minimize wasted spend. One decision per target. Output valid JSON only.

METRICS (calculate from input only, null if division by zero):
- ACoS = Spend / Sales
- ROAS = Sales / Spend
- CTR = Clicks / Impressions

DECISION LOGIC:
| Condition                        | Decision                |
|----------------------------------|-------------------------|
| impressions = 0                  | increase_bid            |
| spend > 0 and sales = 0         | pause / negative_target |
| roas > 3                         | scale / increase_bid    |
| roas 2–3                         | hold                    |
| roas < 2 and sales > 0          | decrease_bid            |

TARGET ROAS (always numeric, never null):
- increase / scale  → 2.5–3.5
- hold              → near current ROAS
- decrease          → 3.0–4.0
- pause / negative  → 4.0+

RULES:
- Use ONLY provided input values. Never invent or estimate.
- suggested_bid: use current_bid if no change is justified.
- confidence_score: integer 0–100.
- No text outside JSON. No markdown. No trailing commas.

OUTPUT SCHEMA:
[
  {
    "entity": "string",
    "decision": "increase_bid | decrease_bid | hold | pause | negative_target | scale",
    "suggested_bid": number,
    "target_roas": number,
    "analysis": {
      "acos": number | null,
      "roas": number | null,
      "ctr_percent": number | null,
      "profitability_assessment": "string",
      "efficiency_assessment": "string"
    },
    "reasoning": "string",
    "confidence_score": integer
  }
]
"""

# ============================================================
# ← ADDED: Pre-filter function — handles 100% deterministic
#   targets instantly in Python, never sends them to GPT-5
# ============================================================
def pre_filter(entity: dict):
    impressions = entity["impressions"]
    spend = entity["spend"]
    sales = entity["sales"]
    current_bid = entity["current_bid"]
    roas = entity["roas"] or 0

    # Zero impressions → increase_bid (visibility issue, no AI needed)
    if impressions == 0:
        return {
            "entity": entity["entity"],
            "decision": "increase_bid",
            "suggested_bid": round(current_bid * 1.2, 2),
            "target_roas": 2.5,
            "analysis": {
                "acos": entity["acos"],
                "roas": entity["roas"],
                "ctr_percent": entity["ctr_percent"],
                "profitability_assessment": "No impressions — visibility issue",
                "efficiency_assessment": "No data to assess"
            },
            "reasoning": "Zero impressions. Increase bid to gain visibility.",
            "confidence_score": 99
        }

    # Spend > 0, Sales = 0 → pause (wasted spend, no AI needed)
    if spend > 0 and sales == 0:
        return {
            "entity": entity["entity"],
            "decision": "pause",
            "suggested_bid": current_bid,
            "target_roas": 4.0,
            "analysis": {
                "acos": entity["acos"],
                "roas": entity["roas"],
                "ctr_percent": entity["ctr_percent"],
                "profitability_assessment": "Spend with zero sales — pure waste",
                "efficiency_assessment": "No conversions detected"
            },
            "reasoning": "Spend with zero sales. Pause to stop wasted budget.",
            "confidence_score": 99
        }

    return None  # Needs AI judgment


# ============================================================
# ← ADDED: Single chunk API call — used by parallel executor
# ============================================================
def call_api_chunk(chunk: list) -> list:
    response = client.chat.completions.create(
        model="anthropic/claude-haiku-4-5",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(chunk)}
        ]
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                return []
        return []


# ============================================================
# ← ADDED: Parallel caller — splits entities into chunks and
#   fires all chunks simultaneously using a thread pool
# ============================================================
def call_api_parallel(entities: list, chunk_size: int = 5) -> list:
    chunks = [entities[i:i+chunk_size] for i in range(0, len(entities), chunk_size)]
    logger.info(f"Splitting {len(entities)} AI targets into {len(chunks)} parallel chunks of {chunk_size}")

    results = []
    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        futures = [executor.submit(call_api_chunk, chunk) for chunk in chunks]
        for future in futures:
            chunk_result = future.result()
            results.extend(chunk_result)

    return results


@router.post("/campaign/{campaign_id}/optimize")
def optimize_campaign(campaign_id: str, request: Request, start_date: str = None, end_date: str = None):

    start_time = time.time()

    logger.info("========== OPTIMIZE ENDPOINT HIT ==========")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Campaign ID: {campaign_id}")
    logger.info(f"Params: start_date={start_date}, end_date={end_date}")

    try:
        # ================= DATABASE =================
        logger.info("Opening database connection")
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        if start_date and end_date:
            logger.info(f"Executing custom range aggregation query: {start_date} to {end_date}")
            query = """
                SELECT
                    target_id,
                    targeting,
                    MAX(keyword_bid) AS current_bid,
                    SUM(impressions) AS impressions,
                    SUM(clicks) AS clicks,
                    SUM(cost) AS spend,
                    SUM(sales_7d) AS sales,
                    SUM(purchases_7d) AS purchases
            FROM sp_targeting_reports
            WHERE campaign_id = %s
              AND report_date BETWEEN %s AND %s
            GROUP BY target_id, targeting
            """
            cursor.execute(query, (campaign_id, start_date, end_date))
        else:
            logger.info("Executing default 30-day aggregation query")
            query = """
                SELECT
                    target_id,
                    targeting,
                    MAX(keyword_bid) AS current_bid,
                    SUM(impressions) AS impressions,
                    SUM(clicks) AS clicks,
                    SUM(cost) AS spend,
                    SUM(sales_7d) AS sales,
                    SUM(purchases_7d) AS purchases
            FROM sp_targeting_reports
            WHERE campaign_id = %s
              AND report_date >= CURDATE() - INTERVAL 30 DAY
            GROUP BY target_id, targeting
            """
            cursor.execute(query, (campaign_id,))
        rows = cursor.fetchall()

        logger.info(f"Fetched {len(rows)} targeting rows from DB")

        cursor.close()
        conn.close()
        logger.info("Database connection closed")

        if not rows:
            logger.warning("No performance data found for this campaign")
            return {
                "success": True,
                "message": "No performance data found for this campaign within the selected date range.",
                "optimization": []
            }

        # ================= PREPARE ENTITIES =================
        entities = []

        for row in rows:
            impressions = int(row["impressions"] or 0)
            clicks = int(row["clicks"] or 0)
            spend = float(row["spend"] or 0)
            sales = float(row["sales"] or 0)
            purchases = int(row["purchases"] or 0)
            current_bid = float(row["current_bid"] or 0)

            ctr = (clicks / impressions) if impressions else 0
            acos = (spend / sales) if sales else 0
            roas = (sales / spend) if spend else 0

            entities.append({
                "entity": row["targeting"],
                "current_bid": current_bid,
                "impressions": impressions,
                "clicks": clicks,
                "ctr_percent": round(ctr * 100, 2),
                "spend": spend,
                "sales": sales,
                "purchases": purchases,
                "acos": round(acos, 3) if acos else None,
                "roas": round(roas, 3) if roas else None
            })

        logger.info(f"Prepared {len(entities)} entities for optimization")

        # ================= PRE-FILTER ← ADDED =================
        instant_results = []   # handled by Python, no API call
        ai_entities = []       # need GPT-5 judgment
        ai_entity_indices = [] # track original index for merge

        for i, entity in enumerate(entities):
            pre_result = pre_filter(entity)
            if pre_result:
                instant_results.append((i, pre_result))
                logger.info(f"Pre-filtered '{entity['entity']}' → {pre_result['decision']} (no API call needed)")
            else:
                ai_entities.append(entity)
                ai_entity_indices.append(i)

        logger.info(f"Pre-filtered: {len(instant_results)} instant | Sending to GPT-5: {len(ai_entities)}")

        # ================= OPENAI CALL (PARALLEL) ← CHANGED =================
        ai_results = []

        if ai_entities:
            logger.info("Calling OpenAI with parallel chunks")
            ai_start = time.time()

            ai_results = call_api_parallel(ai_entities, chunk_size=5)  # ← fires chunks in parallel

            ai_duration = round(time.time() - ai_start, 3)
            logger.info(f"OpenAI parallel response received in {ai_duration} seconds")
        else:
            logger.info("All targets pre-filtered — skipping OpenAI call entirely")

        # ================= MERGE RESULTS =================
        # Build a lookup: original entity index → ai result
        ai_lookup = {}
        for j, ai_row in enumerate(ai_results):
            if j < len(ai_entity_indices):
                original_index = ai_entity_indices[j]
                ai_lookup[original_index] = ai_row

        # Add pre-filtered results to lookup
        for original_index, pre_row in instant_results:
            ai_lookup[original_index] = pre_row

        merged_results = []
        for i, entity in enumerate(entities):
            ai_row = ai_lookup.get(i, {})
            merged_results.append({
                "entity": entity["entity"],
                "current_bid": entity["current_bid"],
                "impressions": entity["impressions"],
                "clicks": entity["clicks"],
                "ctr_percent": entity["ctr_percent"],
                "spend": entity["spend"],
                "sales": entity["sales"],
                "purchases": entity["purchases"],
                "acos": entity["acos"],
                "roas": entity["roas"],
                "decision": ai_row.get("decision"),
                "suggested_bid": ai_row.get("suggested_bid"),
                "target_roas": ai_row.get("target_roas"),
                "confidence_score": ai_row.get("confidence_score"),
                "reasoning": ai_row.get("reasoning")
            })

        logger.info(f"Merged result count: {len(merged_results)}")

        total_time = round(time.time() - start_time, 3)
        logger.info(f"Optimize endpoint completed in {total_time} seconds")
        logger.info("========== OPTIMIZE END ==========")

        return {
            "success": True,
            "message": f"Successfully analyzed {len(entities)} targets for optimization.",
            "campaign_id": campaign_id,
            "optimization": merged_results
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"CRITICAL ERROR in optimize endpoint: {error_msg}")
        
        # Check for OpenRouter 402 - Payment Required
        if "402" in error_msg or "credits" in error_msg.lower():
            return JSONResponse(
                status_code=402,
                content={
                    "success": False,
                    "message": "More Credits needed.",
                    "error": "OpenRouter Credit Depletion"
                }
            )

        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Server Error: {error_msg}",
                "error": error_msg
            }
        )