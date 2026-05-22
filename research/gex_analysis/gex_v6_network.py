import time
import json
import os
from playwright.sync_api import sync_playwright

def run():
    user_data_dir = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_profile"

    with sync_playwright() as p:
        print(f"Launching browser...")
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        # --- LOGIN / HOME ---
        print("Opening home...")
        page.goto("https://gexstream.com/")
        time.sleep(5)
        
        # Ensure login (brief check, assuming profile works)
        if not (page.locator("text=Logout").is_visible() or page.locator("text=Sign Out").is_visible()):
             print("Login check failed (might need manual login if cookies expired, but trying to proceed)")
        
        # --- DATA CAPTURE SETUP ---
        data_store = {
            "qqq": [],
            "spx": []
        }
        current_target = None # "qqq" or "spx"
        
        def handle_response(response):
            if current_target:
                try:
                    # Capture JSON responses that might contain data
                    # Filter by size or keywords to avoid noise
                    if "json" in response.headers.get("content-type", ""):
                        url = response.url
                        # Keywords for relevant APIs
                        if "api" in url or "data" in url or "chart" in url or "quote" in url:
                            try:
                                body = response.json()
                                data_store[current_target].append({
                                    "url": url,
                                    "data": body
                                })
                            except: pass
                except: pass

        context.on("response", handle_response)

        # --- NAVIGATION HELPER ---
        def navigate_and_wait(symbol):
            nonlocal current_target
            current_target = symbol.lower()
            print(f"Navigating to {symbol}...")
            
            # Use Search logic
            search_inputs = page.locator("input[placeholder*='Search'], input[type='search'], input[type='text']").all()
            target_input = None
            for inp in search_inputs:
                if inp.is_visible():
                    target_input = inp
                    break
            
            if target_input:
                target_input.click()
                target_input.fill("") # clear
                target_input.fill(symbol)
                time.sleep(2)
                page.keyboard.press("Enter")
                
                # Wait for potential API calls
                print(f"Waiting 10s for {symbol} data...")
                time.sleep(10)
            else:
                print("Search bar not found during network capture!")

        navigate_and_wait("QQQ")
        navigate_and_wait("SPX")
        
        context.close()
        
        outfile = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\captured_v6.json"
        with open(outfile, "w", encoding='utf-8') as f:
            json.dump(data_store, f, indent=2)
        print("Done.")

if __name__ == "__main__":
    run()
