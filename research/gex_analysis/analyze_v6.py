import json

def find_keys(obj, keywords):
    matches = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            # Check if key matches or if value is a flat number/string we care about
            if any(kw.lower() in k.lower() for kw in keywords):
                matches[k] = v
            # Recurse
            m = find_keys(v, keywords)
            matches.update(m)
    elif isinstance(obj, list):
        for item in obj:
            m = find_keys(item, keywords)
            matches.update(m)
    return matches

def run():
    try:
        with open("captured_v6.json", "r", encoding='utf-8') as f:
            data = json.load(f)
        
        keywords = ["gex", "gamma", "wall", "zero", "spot", "strike", "flip"]
        
        print("--- QQQ Matches ---")
        qqq_matches = find_keys(data["qqq"], keywords)
        # Filter for concise output (avoid huge lists)
        for k, v in list(qqq_matches.items())[:20]: # Limit
            print(f"{k}: {v}")
            
        print("\n--- SPX Matches ---")
        spx_matches = find_keys(data["spx"], keywords)
        for k, v in list(spx_matches.items())[:20]:
            print(f"{k}: {v}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()
