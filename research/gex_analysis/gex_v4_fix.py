import time
import json
import os
from playwright.sync_api import sync_playwright

def run():
    EMAIL = "ryanli38572331@gmail.com"
    PASS = "LfXhCjD!f4!T72x"
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
        
        # --- LOGIN ---
        print("Opening home...")
        page.goto("https://gexstream.com/")
        time.sleep(3)
        
        if page.locator("text=Logout").is_visible() or page.locator("text=Sign Out").is_visible() or "dashboard" in page.url:
             print("Already logged in.")
        else:
            print("Auto-login...")
            try:
                # Try explicit login URL if button not found quickly
                if not page.locator("input[type='password']").is_visible():
                    page.goto("https://gexstream.com/login")
                    time.sleep(2)
                
                if page.locator("input[name='email']").is_visible():
                    page.fill("input[name='email']", EMAIL)
                    page.fill("input[name='password']", PASS)
                    page.click("button[type='submit']")
                    page.wait_for_url("**/dashboard**", timeout=15000)
                    print("Login success.")
            except Exception as e:
                print(f"Login warning: {e}")

        time.sleep(3)

        # --- DATA CAPTURE SETUP ---
        data_store = {
            "qqq": {"json": [], "text": "", "meta": {}},
            "spx": {"json": [], "text": "", "meta": {}}
        }
        current_target = None
        
        def handle_response(response):
            try:
                if current_target and "json" in response.headers.get("content-type", ""):
                    # Capture everything that looks like API data
                    if "api" in response.url or "chart" in response.url:
                        try:
                            data_store[current_target]["json"].append({
                                "url": response.url,
                                "data": response.json()
                            })
                        except: pass
            except: pass

        context.on("response", handle_response)
        
        def force_navigate(symbol):
            print(f"Navigating to {symbol}...")
            # Try Direct URL
            page.goto(f"https://gexstream.com/quote/{symbol}")
            time.sleep(5)
            
            # Check if 404 or empty
            text = page.evaluate("document.body.innerText")
            if "404" in text or "not found" in text.lower():
                print("Direct URL failed. Using Search...")
                try:
                    # Try clicking dashboard or home first to reset
                    page.goto("https://gexstream.com/dashboard") 
                    time.sleep(3)
                    
                    # Search
                    # Selectors for search input
                    search = page.locator("input[placeholder*='Search'], input[type='search']").first
                    if search.is_visible():
                        search.click()
                        search.fill(symbol)
                        time.sleep(2)
                        page.keyboard.press("Enter")
                        time.sleep(5)
                    else:
                        print("Search bar not found!")
                except Exception as e:
                    print(f"Search failed: {e}")
            
            # Additional cleanup/verification
            time.sleep(5)
            return page.url

        # --- CAPTURE QQQ ---
        current_target = "qqq"
        url = force_navigate("QQQ")
        print(f"On URL: {url}")
        
        # Scroll to trigger lazy loading
        page.mouse.wheel(0, 1000)
        time.sleep(10)
        
        # Scrape text specifically for Key Levels if they are in DOM
        # Try to find elements that look like "Net GEX", "Zero Gamma", etc.
        try:
            data_store["qqq"]["text"] = page.evaluate("document.body.innerText")
        except: pass

        # --- CAPTURE SPX ---
        current_target = "spx"
        url = force_navigate("SPX")
        print(f"On URL: {url}")
        
        page.mouse.wheel(0, 1000)
        time.sleep(10)
        
        try:
            data_store["spx"]["text"] = page.evaluate("document.body.innerText")
        except: pass
        
        context.close()
        
        outfile = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\captured_v4.json"
        with open(outfile, "w", encoding='utf-8') as f:
            json.dump(data_store, f, indent=2, ensure_ascii=False)
        print("Done.")

if __name__ == "__main__":
    run()
