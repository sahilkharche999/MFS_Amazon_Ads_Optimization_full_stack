from fastapi import APIRouter
from app.database import get_connection
from openai import OpenAI
import os, json
import pymysql
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

SYSTEM_PROMPT = """
You are a senior Amazon Sponsored Products optimization strategist specializing in book publishing.

MISSION:
Your purpose is to analyze target-level Amazon Ads advertising performance for book marketing and produce strategic optimization recommendations using ACoS as the leading indicator metric and return one optimization decision per target.

OBJECTIVE:
Maximize profitable scale while minimizing wasted spend.

PRIMARY METRICS (calculate exactly from provided data):
ACoS = Spend ÷ Sales (if Sales > 0)
ROAS = Sales ÷ Spend (if Spend > 0)
CTR = Clicks ÷ Impressions (if Impressions > 0)

DECISIONS (choose one):
increase_bid | decrease_bid | hold | pause | negative_target | scale

CORE LOGIC (guideline, not rigid):
sales = 0 and spend > 0 → pause or negative_target
impressions = 0 → increase_bid (visibility issue)
roas > 3 → scale or increase_bid
roas 2-3 → hold
roas < 2 and sales > 0 → decrease_bid

Analyze performance holistically. Consider:
- Visibility
- Conversion efficiency
- Profitability
- Scale potential
- Waste risk

Provide reasoning that references:
- Spend, Sales, ROAS, ACoS, CTR, Impression volume
Explain WHY the decision improves profitability or scale.

STRICT RULES:
Use ONLY the numbers provided in the input.
NEVER invent or estimate missing values.
If a metric cannot be calculated (division by zero), return null.
suggested_bid must be a numeric value (use current_bid if no change is justified).
target_roas must be numeric or null.
confidence_score must be an integer between 0 and 100.
Do NOT include commentary outside the JSON.
Do NOT include markdown formatting.
Output must be valid JSON.
Output must be a JSON array.
No trailing commas.
No additional fields beyond the defined schema.

OUTPUT SCHEMA (must match exactly):
[
{
"entity": "string",
"decision": "increase_bid | decrease_bid | hold | pause | negative_target",
"suggested_bid": number,
"target_roas": number | null,
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

Return ONLY the JSON array.
No markdown.
No explanations.
No text before or after the JSON.
"""

@router.post("/campaign/{campaign_id}/optimize")
def optimize_campaign(campaign_id: str):

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

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
      AND report_date >= CURDATE() - INTERVAL 14 DAY
    GROUP BY target_id, targeting
    """

    cursor.execute(query, (campaign_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return {"optimization": []}

    entities = []

    for row in rows:
        impressions = int(row["impressions"] or 0)
        clicks = int(row["clicks"] or 0)
        spend = float(row["spend"] or 0)
        sales = float(row["sales"] or 0)
        purchases = int(row["purchases"] or 0)
        current_bid = float(row["current_bid"] or 0)

        ctr = (clicks / impressions) if impressions else 0
        acos = (spend / sales) if sales else None
        roas = (sales / spend) if spend else None

        entities.append({
            "entity": row["targeting"],
            "current_bid": current_bid,
            "impressions": impressions,
            "clicks": clicks,
            "ctr_percent": round(ctr * 100, 2),
            "spend": spend,
            "sales": sales,
            "purchases": purchases,
            "acos": round(acos, 3) if acos is not None else None,
            "roas": round(roas, 3) if roas is not None else None
        })

    response = client.chat.completions.create(
        model="openai/gpt-5",
        temperature=0.2,
        # response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(entities)}
        ]
    )

    # result = json.loads(response.choices[0].message.content)
    raw_content = response.choices[0].message.content

    # direct parse
    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError:
        print("⚠️ GPT returned invalid JSON. Raw output below:")
        print(raw_content)

        # Fallback: attempt to extract JSON array manually
        import re
        match = re.search(r"\[.*\]", raw_content, re.DOTALL)

        if match:
            try:
                result = json.loads(match.group())
            except:
                result = []
        else:
            result = []

   # Step 2: If result is still string, try parsing again 
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            result = []

    # Step 3: Ensure result is list
    if not isinstance(result, list):
        result = []

    if isinstance(result, dict) and "results" in result:
        result = result["results"]

    # Step 4: Ensure every item is dict
    cleaned_result = []
    for item in result:
        if isinstance(item, dict):
            cleaned_result.append(item)
        elif isinstance(item, str):
            try:
                parsed_item = json.loads(item)
                if isinstance(parsed_item, dict):
                    cleaned_result.append(parsed_item)
            except:
                continue

    result = cleaned_result

    merged_results = []

    for index, ai_row in enumerate(result):

        if index >= len(entities):
            continue

        matching_entity = entities[index]

        merged_results.append({
            "entity": matching_entity["entity"],
            "current_bid": matching_entity["current_bid"],
            "impressions": matching_entity["impressions"],
            "clicks": matching_entity["clicks"],
            "ctr_percent": matching_entity["ctr_percent"],
            "spend": matching_entity["spend"],
            "sales": matching_entity["sales"],
            "purchases": matching_entity["purchases"],
            "acos": matching_entity["acos"],
            "roas": matching_entity["roas"],
            "decision": ai_row.get("decision"),
            "suggested_bid": ai_row.get("suggested_bid"),
            "target_roas": ai_row.get("target_roas"),
            "confidence_score": ai_row.get("confidence_score"),
            "reasoning": ai_row.get("reasoning")
        })

    return {
        "campaign_id": campaign_id,
        "optimization": merged_results
    }
