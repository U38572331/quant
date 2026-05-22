from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.client import DeribitClient
from src.utils import enrich_data
from src.calculator import AdvancedCalculator
from src.analytics import MarketAnalyzer
import pandas as pd
import uvicorn
import numpy as np
import os

app = FastAPI(title="Deribit GEX API")

# Enable CORS (still good practice)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints First
@app.get("/api/v1/snapshot/{currency}")
def get_market_snapshot(currency: str = "BTC"):
    try:
        # 1. Fetch Data
        client = DeribitClient()
        instruments = client.get_instruments(currency)
        summary = client.get_book_summary_by_currency(currency)
        
        # Spot Price
        index_name = f"{currency.lower()}_usd"
        real_spot = client.get_index_price(index_name)
        
        if instruments.empty or summary.empty:
            raise HTTPException(status_code=503, detail="Deribit API unavailable")
            
        # 2. Enrich & Calculate
        df = enrich_data(instruments, summary, real_spot)
        calc = AdvancedCalculator()
        df = calc.process_dataframe(df)
        
        # 3. Analyze
        analyzer = MarketAnalyzer(df)
        analyzer.clean_data()
        analyzer.current_price = df['underlying_price'].iloc[0] if not df.empty else 0
        
        # Structural Expiry
        struct_exp = analyzer.get_dominant_structural_expiry()
        if not struct_exp:
            # Fallback to next major or just largest OI
            struct_exp = df['expiry_date'].max() # Crude fallback
        
        # Filter for Structural analysis
        analyzer_struct = MarketAnalyzer(df[df['expiry_date'] == struct_exp])
        gex_struct_df = analyzer_struct.calculate_dealer_gamma_profile() # Correct method name
        
        # Metrics
        flip = analyzer.find_flip_level(gex_struct_df)
        max_pain = analyzer_struct.calculate_max_pain()
        
        # -- Phase 7 Expansion --
        term_structure = analyzer.get_term_structure()
        top_pos, top_neg = analyzer.get_top_gex_strikes(gex_struct_df, n=5)
        sentiment = analyzer.get_sentiment_metrics()
        
        # -- Phase 8 Expansion --
        gex_surface = analyzer.get_gex_surface()
        oi_profile_df = analyzer.get_oi_profile()
        oi_profile = oi_profile_df.to_dict('records') if not oi_profile_df.empty else []
        
        # Unified Curve
        curve_data = analyzer.get_gex_curve(gex_struct_df, num_points=200)
        
        # Summary
        summary_html = analyzer.generate_ai_summary(gex_struct_df, flip, max_pain)
        
        # Prepare JSON Response
        response = {
            "timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
            "spot_price": analyzer.current_price,
            "structural_expiry": struct_exp.isoformat() if struct_exp else None,
            "metrics": {
                "max_pain": max_pain,
                "flip_level": flip,
                "total_gex": gex_struct_df['net_gex'].sum() if not gex_struct_df.empty else 0,
                "pcr_oi": sentiment.get('pcr_oi', 0),
                "total_oi": sentiment.get('total_oi', 0)
            },
            "term_structure": term_structure,
            "top_strikes": {
                "positive": top_pos,
                "negative": top_neg
            },
            "summary_html": summary_html,
            "curve": {
                "x": curve_data['x'].tolist() if curve_data else [],
                "y": curve_data['y'].tolist() if curve_data else [],
                "color_pos": "#00e676",
                "color_neg": "#ff1744"
            },
            "market_status": {
                "is_connected": True,
                "row_count": len(df)
            },
            "gex_surface": gex_surface,
            "oi_profile": oi_profile
        }
        
        return sanitize_json(response)
        
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_index():
    return FileResponse('web/index.html')

@app.get("/style.css")
async def read_css():
    return FileResponse('web/style.css')

@app.get("/script.js")
async def read_js():
    return FileResponse('web/script.js')

@app.get("/health")
def health_check():
    return {"status": "online", "version": "2.0.0"}

# Mount Static Files (Must be after API routes to avoid conflict if not careful, but here /api is distinct)
# Check if web directory exists
if os.path.exists("web"):
    app.mount("/static", StaticFiles(directory="web"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
