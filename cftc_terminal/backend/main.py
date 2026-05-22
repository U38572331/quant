from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.data_engine import CFTCDataEngine
import os
import uvicorn
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = CFTCDataEngine()
engine = CFTCDataEngine()

@app.get("/api/markets")
def get_markets():
    return engine.get_market_list()

@app.get("/api/data/{code}")
def get_data(code: str):
    data = engine.get_market_history(code)
    return data if data else []

@app.get("/api/update")
def force_update():
    count = engine.fetch_recent_data(limit=5000)
    return {"status": "success", "rows": count}

# Mount
frontend = os.path.join(os.getcwd(), "frontend")
if os.path.exists(frontend):
    app.mount("/", StaticFiles(directory=frontend, html=True), name="static")

if __name__ == "__main__":
    # Initial Data Fetch on Startup (Non-Blocking)
    print("--- SERVER STARTING ---")
    
    def background_seed():
        import time
        time.sleep(2) # Let server start
        print("--- BACKGROUND SYNC STARTED ---")
        engine.ingest_full_history()
        print("--- BACKGROUND SYNC COMPLETE ---")
    
    t = threading.Thread(target=background_seed)
    t.daemon = True
    t.start()
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
