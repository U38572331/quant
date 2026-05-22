import time
import json
import os
from playwright.sync_api import sync_playwright

def run():
    # Use a persistent user data directory so login is saved
    user_data_dir = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_profile"
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    with sync_playwright() as p:
        print(f"Launching browser with profile at {user_data_dir}...")
        # persistent_context launches a browser that uses the given user data dir
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 720}
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        print("Opening gexstream.com...")
        page.goto("https://gexstream.com/")
        
        print("Please log in manually if needed. Waiting for Dashboard...")
        print("Keep this window open.")
        
        # Wait for login
        logged_in = False
        while not logged_in:
            try:
                # Check for common post-login indicators
                if (page.locator("text=Logout").is_visible() or 
                    page.locator("text=Sign Out").is_visible() or 
                    "dashboard" in page.url or 
                    "app" in page.url):
                    logged_in = True
                    print("Login detected! Proceeding...")
                else:
                    time.sleep(1)
            except Exception as e:
                time.sleep(1)
        
        # Setup comprehensive interception
        data_store = {
            "qqq": {"json": [], "ws": [], "text": ""},
            "spx": {"json": [], "ws": [], "text": ""}
        }
        current_target = None
        
        def handle_response(response):
            try:
                if current_target:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        try:
                            data_store[current_target]["json"].append({
                                "url": response.url,
                                "data": response.json()
                            })
                        except: pass
            except: pass

        def handle_ws_frame(data):
            try:
                if current_target:
                    # Try to decode text or keep mostly text-based frames
                    if isinstance(data, str):
                        data_store[current_target]["ws"].append(data)
                    elif isinstance(data, bytes):
                        try:
                            decoded = data.decode('utf-8')
                            data_store[current_target]["ws"].append(decoded)
                        except: 
                            pass # Ignore binary blobs
            except: pass

        context.on("response", handle_response)
        
        # Hook into websockets
        def on_websocket(ws):
            ws.on("framereceived", lambda frame: handle_ws_frame(frame))
        
        page.on("websocket", on_websocket)
        
        # --- Phase 1: QQQ ---
        current_target = "qqq"
        print("Navigating to QQQ...")
        
        try:
            # Attempt navigation
            search_input = page.locator("input[placeholder*='Search'], input[placeholder*='Symbol']").first
            if search_input.is_visible():
                print("Using search bar...")
                search_input.fill("QQQ")
                time.sleep(1)
                page.keyboard.press("Enter")
                time.sleep(2)
                # handle dropdown
                first_res = page.locator(".search-result, .dropdown-item").first
                if first_res.is_visible():
                    first_res.click()
            else:
                print("Direct navigation to /quote/QQQ")
                page.goto("https://gexstream.com/quote/QQQ")
        except:
            print("Navigation failed. Please navigate to QQQ manually.")

        print("Collecting QQQ data for 15 seconds...")
        time.sleep(15) 
        # Scrape text
        try:
            data_store["qqq"]["text"] = page.evaluate("document.body.innerText")
        except: pass
        
        # --- Phase 2: SPX ---
        current_target = "spx"
        print("Navigating to SPX...")
        try:
             # Look for search again to switch
            search_input = page.locator("input[placeholder*='Search'], input[placeholder*='Symbol']").first
            if search_input.is_visible():
                print("Using search bar...")
                search_input.fill("SPX")
                time.sleep(1)
                page.keyboard.press("Enter")
                time.sleep(2)
                first_res = page.locator(".search-result, .dropdown-item").first
                if first_res.is_visible():
                    first_res.click()
            else:
                 page.goto("https://gexstream.com/quote/SPX")
        except:
             print("Navigation failed.")
             
        print("Collecting SPX data for 15 seconds...")
        time.sleep(15)
        try:
            data_store["spx"]["text"] = page.evaluate("document.body.innerText")
        except: pass
        
        context.close()
        
        outfile = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\captured_v2.json"
        with open(outfile, "w", encoding='utf-8') as f:
            json.dump(data_store, f, indent=2, ensure_ascii=False)
        print("Done.")

if __name__ == "__main__":
    run()
