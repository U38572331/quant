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
        
        # --- LOGIN / HOME ---
        print("Opening home...")
        page.goto("https://gexstream.com/")
        time.sleep(5)
        
        # Check login
        if not (page.locator("text=Logout").is_visible() or page.locator("text=Sign Out").is_visible()):
             try:
                 print("Attempting login...")
                 if page.locator("input[name='email']").is_visible():
                     page.fill("input[name='email']", EMAIL)
                     page.fill("input[name='password']", PASS)
                     page.click("button[type='submit']")
                     time.sleep(5)
                 else:
                     # Check if there is a login button to click first
                     login_btn = page.locator("a[href='/login'], button:has-text('Login')").first
                     if login_btn.is_visible():
                         login_btn.click()
                         time.sleep(3)
                         if page.locator("input[name='email']").is_visible():
                             page.fill("input[name='email']", EMAIL)
                             page.fill("input[name='password']", PASS)
                             page.click("button[type='submit']")
                             time.sleep(5)
             except Exception as e:
                 print(f"Login logic error: {e}")

        # Ensure we are at home and loaded
        page.goto("https://gexstream.com/")
        print("Waiting for app execution...")
        time.sleep(5)
        
        # --- DATA CAPTURE SETUP ---
        data_store = {
            "qqq": {"net_gex": None, "zero_gamma": None, "call_wall": None, "put_wall": None, "text": ""},
            "spx": {"net_gex": None, "zero_gamma": None, "call_wall": None, "put_wall": None, "text": ""}
        }

        # --- NAVIGATION & CAPTURE FUNCTION ---
        def capture_target(symbol):
            print(f"--- Capturing {symbol} ---")
            
            # 1. Search
            search_found = False
            # Broad search for any input that could be search
            search_inputs = page.locator("input").all()
            target_input = None
            for inp in search_inputs:
                try:
                    ph = inp.get_attribute("placeholder")
                    if ph and ("Search" in ph or "Symbol" in ph or "Ticker" in ph):
                        target_input = inp
                        break
                except: pass
            
            if not target_input and len(search_inputs) > 0:
                 # Guess the first text input if no placeholder matches
                 for inp in search_inputs:
                     if inp.get_attribute("type") in ["text", "search"]:
                         target_input = inp
                         break
            
            if target_input and target_input.is_visible():
                print("Found search bar. Typing...")
                target_input.click()
                target_input.fill(symbol)
                time.sleep(2)
                # Press Enter
                page.keyboard.press("Enter")
                time.sleep(5) # Wait for navigation
                
                # Check for dropdown results if Enter didn't work immediately
                try:
                    res = page.locator(".result-item, .search-result").first
                    if res.is_visible():
                        res.click()
                        time.sleep(5)
                except: pass
                
            else:
                print("Search bar NOT found. Inspecting page text for debug...")
                print(page.evaluate("document.body.innerText")[:200])
                return

            # 2. Extract Data
            # We will scrape the text and try to find the keywords
            # Keywords: "Net GEX", "Zero Gamma", "Call Wall", "Put Wall"
            full_text = page.evaluate("document.body.innerText")
            data_store[symbol.lower()]["text"] = full_text # Save full text for safety
            
            # Simple text parsing helper
            def extract_val(key, text):
                # Look for "Key: Value" or "Key \n Value" pattern
                try:
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if key.lower() in line.lower():
                            # Check next line or same line
                            parts = line.split(key)
                            if len(parts) > 1 and parts[1].strip():
                                return parts[1].strip()
                            elif i + 1 < len(lines):
                                return lines[i+1].strip()
                except: pass
                return "N/A"

            data_store[symbol.lower()]["net_gex"] = extract_val("Net GEX", full_text)
            data_store[symbol.lower()]["zero_gamma"] = extract_val("Zero Gamma", full_text)
            data_store[symbol.lower()]["call_wall"] = extract_val("Call Wall", full_text)
            data_store[symbol.lower()]["put_wall"] = extract_val("Put Wall", full_text)
            
            print(f"Extracted for {symbol}: {data_store[symbol.lower()]}")

        # Capture QQQ
        capture_target("QQQ")
        
        # Capture SPX
        # Note: Need to clear search or go home? 
        # Usually search bar persists. Let's click it again.
        capture_target("SPX")
        
        context.close()
        
        outfile = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\final_data.json"
        with open(outfile, "w", encoding='utf-8') as f:
            json.dump(data_store, f, indent=2)
        print("Done.")

if __name__ == "__main__":
    run()
