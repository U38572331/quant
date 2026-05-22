import os
import time

path = r"c:\Users\user\.gemini\antigravity\scratch\data\review_queue.json"
state_path = r"c:\Users\user\.gemini\antigravity\scratch\data\state.json"

def clean():
    # 1. Clear Strategy Queue
    if os.path.exists(path):
        try:
            with open(path, "w") as f:
                f.write("[]")
            print(f"SUCCESS: {path} has been truncated to 0 points.")
        except Exception as e:
            print(f"ERROR: Could not truncate queue: {e}")
    else:
        print("Queue file not found, clean start assumed.")

    # 2. Reset Agent State
    if os.path.exists(state_path):
        try:
            with open(state_path, "w") as f:
                f.write('{"agent": {"status": "Starting...", "generation": 0, "best_sharpe": 0.0, "last_update": "Reset"}}')
            print(f"SUCCESS: {state_path} reset.")
        except:
            pass

if __name__ == "__main__":
    clean()
