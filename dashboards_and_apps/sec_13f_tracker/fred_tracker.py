import requests
import json
import os
from datetime import datetime, timedelta
import random
import statistics
import math

# --- Configuration ---
API_KEY = os.getenv("FRED_API_KEY", "") 
OUTPUT_FILE = "public/macro.json"

# Categorized Series (42 Series Suite)
CATEGORIES = {
    "Liquidity": {
        "WALCL": "Total Assets (Fed Balance Sheet)",
        "WTREGEN": "Treasury General Account",
        "RRPONTSYD": "Overnight Reverse Repos",
        "WRESBAL": "Reserve Balances at Fed"
    },
    "Rates": {
        "EFFR": "Fed Funds Rate",
        "SOFR": "SOFR Rate",
        "IORB": "Interest on Reserve Balances",
        "OBFR": "Overnight Bank Funding Rate"
    },
    "YieldCurve": {
        "DGS3MO": "3-Month Treasury",
        "DGS2": "2-Year Treasury",
        "DGS10": "10-Year Treasury",
        "T10Y2Y": "10Y-2Y Spread",
        "T10Y3M": "10Y-3M Spread"
    },
    "Inflation": {
        "PCEPI": "PCE Price Index (YoY)",
        "CPIAUCSL": "Consumer Price Index",
        "T5YIE": "5Y Breakeven Inflation",
        "T10YIE": "10Y Breakeven Inflation"
    },
    "Credit": {
        "BAMLH0A0HYM2": "High Yield Spread",
        "BAMLC0A0CM": "Baa Corporate Bond Yield",
        "NFCI": "Chicago Fed Financial Conditions Index"
    },
    "Volatility": {
        "VIXCLS": "VIX Index",
        "MOVE": "MOVE Index (Bonds)"
    },
    "Global": {
        "DTWEXBGS": "Broad Dollar Index",
        "DTWEXM": "Major Currencies Dollar Index"
    },
    "Consumption": {
        "RSAFS": "Retail Sales",
        "UMCSENT": "Consumer Sentiment",
        "PSAVERT": "Personal Savings Rate"
    },
    "Housing": {
        "HOUST": "Housing Starts",
        "PERMIT": "Building Permits",
        "MORTGAGE30US": "30Y Mortgage Rate"
    },
    "Labor": {
        "PAYEMS": "Nonfarm Payrolls",
        "UNRATE": "Unemployment Rate",
        "JTSJOL": "Job Openings (JOLTS)",
        "ICSA": "Initial Claims"
    },
    "Industrial": {
        "INDPRO": "Industrial Production",
        "IPMAN": "Manufacturing Output",
        "TCU": "Capacity Utilization"
    }
}

# Directionality: 1 if higher is "better/expansionary", -1 if higher is "worse/stress"
DIRECTION = {
    "WALCL": 1, "WTREGEN": -1, "RRPONTSYD": -1, "WRESBAL": 1,
    "EFFR": -1, "SOFR": -1, "IORB": -1, "OBFR": -1,
    "DGS3MO": -1, "DGS2": -1, "DGS10": -1, "T10Y2Y": 1, "T10Y3M": 1,
    "PCEPI": -1, "CPIAUCSL": -1, "T5YIE": 1, "T10YIE": 1,
    "BAMLH0A0HYM2": -1, "BAMLC0A0CM": -1, "NFCI": -1,
    "VIXCLS": -1, "MOVE": -1,
    "DTWEXBGS": -1, "DTWEXM": -1,
    "RSAFS": 1, "UMCSENT": 1, "PSAVERT": 1,
    "HOUST": 1, "PERMIT": 1, "MORTGAGE30US": -1,
    "PAYEMS": 1, "UNRATE": -1, "JTSJOL": 1, "ICSA": -1,
    "INDPRO": 1, "IPMAN": 1, "TCU": 1
}

def fetch_series(series_id, api_key):
    if not api_key:
        return generate_mock_data(series_id)
    
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 100 # Fetch more for Z-score calculation
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        points = [
            {"date": obs["date"], "value": float(obs["value"]) if obs["value"] != "." else None}
            for obs in data["observations"]
            if obs["value"] != "."
        ][::-1]
        return points
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return generate_mock_data(series_id)

def generate_mock_data(series_id):
    data = []
    end_date = datetime.now()
    configs = {
        "WALCL": {"base": 7.5e12, "vol": 1e10, "trend": -5e9},
        "WTREGEN": {"base": 7e11, "vol": 5e10, "trend": 0},
        "RRPONTSYD": {"base": 4e11, "vol": 5e10, "trend": -2e10},
        "WRESBAL": {"base": 3.2e12, "vol": 2e10, "trend": 0},
        "EFFR": {"base": 5.33, "vol": 0.05, "trend": 0},
        "SOFR": {"base": 5.32, "vol": 0.05, "trend": 0},
        "IORB": {"base": 5.4, "vol": 0, "trend": 0},
        "OBFR": {"base": 5.31, "vol": 0.05, "trend": 0},
        "VIXCLS": {"base": 15, "vol": 2, "trend": 0.1},
        "UNRATE": {"base": 4.1, "vol": 0.1, "trend": 0.01},
        "DGS10": {"base": 4.25, "vol": 0.1, "trend": -0.01},
        "T10Y2Y": {"base": -0.4, "vol": 0.05, "trend": 0.01},
        "RSAFS": {"base": 700000, "vol": 5000, "trend": 1000},
        "UMCSENT": {"base": 65, "vol": 2, "trend": 0.5},
        "HOUST": {"base": 1400, "vol": 50, "trend": 10},
        "PCEPI": {"base": 120, "vol": 0.5, "trend": 0.2}
    }
    conf = configs.get(series_id, {"base": 100 if "PRO" in series_id else 5, "vol": 2, "trend": 0.1})
    current_val = conf["base"]
    for i in range(100):
        dt = end_date - timedelta(days=30 * (99 - i)) if "W" not in series_id else end_date - timedelta(weeks=(99-i))
        current_val += conf["trend"] + (random.random() - 0.5) * conf["vol"]
        data.append({"date": dt.strftime("%Y-%m-%d"), "value": round(float(current_val), 4)})
    return data

def calculate_analytics(observations, series_id):
    if not observations: return {}
    vals = [o["value"] for o in observations if o["value"] is not None]
    if len(vals) < 5: return {}
    
    current = vals[-1]
    prev_7d = vals[-2] if len(vals) > 1 else current
    prev_30d = vals[-5] if len(vals) > 5 else vals[0]
    prev_90d = vals[-12] if len(vals) > 12 else vals[0]
    
    # Simple change rates
    chg_7d = (current - prev_7d) / prev_7d if prev_7d != 0 else 0
    chg_30d = (current - prev_30d) / prev_30d if prev_30d != 0 else 0
    chg_90d = (current - prev_90d) / prev_90d if prev_90d != 0 else 0
    
    # Z-Score (relative to whole history fetched)
    mean = statistics.mean(vals)
    stdev = statistics.stdev(vals) if len(vals) > 1 else 1
    z_score = (current - mean) / stdev if stdev != 0 else 0
    
    return {
        "current": current,
        "chg_7d": round(chg_7d, 4),
        "chg_30d": round(chg_30d, 4),
        "chg_90d": round(chg_90d, 4),
        "z_score": round(z_score, 2),
        "direction": DIRECTION.get(series_id, 1)
    }

def main():
    print("🚀 Synchronizing Advanced Macro Analytics Engine...")
    result = {
        "generated_at": datetime.now().isoformat(),
        "is_mock": not bool(API_KEY),
        "categories": {},
        "summary": {}
    }
    
    category_scores = {}
    
    for cat, series in CATEGORIES.items():
        print(f"  Processing Category: {cat}...")
        result["categories"][cat] = {"score": 0, "series": {}}
        cat_z_sum = 0
        cat_count = 0
        
        for sid, name in series.items():
            print(f"    Fetching {sid}...")
            obs = fetch_series(sid, API_KEY)
            analytics = calculate_analytics(obs, sid)
            
            result["categories"][cat]["series"][sid] = {
                "name": name,
                "history": obs[-60:], # Keep last 60 for UI charts
                "analytics": analytics
            }
            
            if analytics:
                # Contribution to score: Z-score * Direction
                # We normalize Z-score to a 0-100 score where 0 is stress, 100 is expansion
                # A Z-score of 0 (mean) = 50. Z-score of +2 (extension) = 90, -2 = 10.
                norm_score = 50 + (analytics["z_score"] * analytics["direction"] * 20)
                norm_score = max(0, min(100, norm_score))
                cat_z_sum += norm_score
                cat_count += 1
        
        if cat_count > 0:
            category_scores[cat] = round(cat_z_sum / cat_count, 1)
            result["categories"][cat]["score"] = category_scores[cat]

    # Global Regime Analysis
    global_score = statistics.mean(category_scores.values()) if category_scores else 50
    regime = "NEUTRAL"
    if global_score > 70: regime = "EXPANSIONARY"
    elif global_score > 55: regime = "STABLE / POSITIVE"
    elif global_score < 30: regime = "CRISIS / STRESS"
    elif global_score < 45: regime = "CONTRACTIONARY"
    
    result["summary"] = {
        "global_score": round(global_score, 1),
        "regime": regime,
        "sentiment": "bullish" if global_score > 55 else "bearish" if global_score < 45 else "neutral"
    }
    
    if not os.path.exists("public"): os.makedirs("public")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
        
    print(f"\n✅ Advanced Macro Data saved to {OUTPUT_FILE} (Regime: {regime})")

if __name__ == "__main__":
    main()
