import time
import json
import os
from playwright.sync_api import sync_playwright

def run():
    # Credentials
    EMAIL = "ryanli38572331@gmail.com"
    PASS = "LfXhCjD!f4!T72x"

    # Use a persistent user data directory
    user_data_dir = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_profile"
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    with sync_playwright() as p:
        print(f"Launching browser with profile at {user_data_dir}...")
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 720},
            # Add args to help with possible anti-bot but standard playwright usually works for this site
            args=["--disable-blink-features=AutomationControlled"] 
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        print("Opening gexstream.com...")
        page.goto("https://gexstream.com/")
        time.sleep(3)

        # Check if already logged in
        if page.locator("text=Logout").is_visible() or page.locator("text=Sign Out").is_visible() or "dashboard" in page.url or "app" in page.url:
             print("Already logged in.")
        else:
            print("Not logged in. Attempting auto-login...")
            # Try to find login button
            login_btn = page.locator("a[href*='login'], button:has-text('Login')").first
            if login_btn.is_visible():
                login_btn.click()
                time.sleep(2)
            
            # Fill credentials
            print("Filling credentials...")
            try:
                page.fill("input[name='email'], input[type='email']", EMAIL)
                page.fill("input[name='password'], input[type='password']", PASS)
                page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Log In')")
                print("Submitted login form.")
                
                # Wait for navigation or success
                page.wait_for_url("**/dashboard**", timeout=15000)
                print("Login successful (url contains dashboard).")
            except Exception as e:
                print(f"Login automation encountered an issue: {e}")
                print("Please intervene manually if needed.")

        # Ensure we are on dashboard or app
        time.sleep(5)
        
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
                    if isinstance(data, str):
                        data_store[current_target]["ws"].append(data)
                    elif isinstance(data, bytes):
                        try:
                            decoded = data.decode('utf-8')
                            data_store[current_target]["ws"].append(decoded)
                        except: pass
            except: pass

        context.on("response", handle_response)
        
        def on_websocket(ws):
            ws.on("framereceived", lambda frame: handle_ws_frame(frame))
        page.on("websocket", on_websocket)
        
        # --- Phase 1: QQQ ---
        current_target = "qqq"
        print("Navigating to QQQ...")
        
        try:
            # Force navigation to ensure we aren't just purely relying on search
            page.goto("https://gexstream.com/result/QQQ") # Try specific result URL structure first if known, else standard search
            # Fallback/alternative: Use search bar if the direct link isn't right
            if "QQQ" not in page.url and "qqq" not in page.url:
                 print("Direct link might have failed, trying search bar...")
                 search_input = page.locator("input[placeholder*='Search'], input[placeholder*='Symbol']").first
                 if search_input.is_visible():
                    search_input.fill("QQQ")
                    time.sleep(1)
                    page.keyboard.press("Enter")
                    time.sleep(2)
                    first_res = page.locator(".search-result, .dropdown-item").first
                    if first_res.is_visible():
                        first_res.click()
        except Exception as e:
            print(f"Navigation error: {e}")

        print("Collecting QQQ data for 15 seconds...")
        time.sleep(15) 
        try:
            data_store["qqq"]["text"] = page.evaluate("document.body.innerText")
        except: pass
        
        # --- Phase 2: SPX ---
        current_target = "spx"
        print("Navigating to SPX...")
        try:
             page.goto("https://gexstream.com/result/SPX")
             if "SPX" not in page.url and "spx" not in page.url:
                 search_input = page.locator("input[placeholder*='Search'], input[placeholder*='Symbol']").first
                 if search_input.is_visible():
                    search_input.fill("SPX")
                    time.sleep(1)
                    page.keyboard.press("Enter")
                    time.sleep(2)
                    first_res = page.locator(".search-result, .dropdown-item").first
                    if first_res.is_visible():
                        first_res.click()
        except:
             print("Navigation failed.")
             
        print("Collecting SPX data for 15 seconds...")
        time.sleep(15)
        try:
            data_store["spx"]["text"] = page.evaluate("document.body.innerText")
        except: pass
        
        context.close()
        
        outfile = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\captured_v3.json"
        with open(outfile, "w", encoding='utf-8') as f:
            json.dump(data_store, f, indent=2, ensure_ascii=False)
        print("Done.")

if __name__ == "__main__":
    run()
