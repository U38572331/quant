from backend.data_engine import CFTCDataEngine
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)

print("--- STARTING STANDALONE INGEST ---")
engine = CFTCDataEngine()

# Try a smaller chunk size to be safe, and verify it loops
total = engine.ingest_full_history(chunk_size=5000)

print(f"--- INGEST FINISHED. Total: {total} ---")
