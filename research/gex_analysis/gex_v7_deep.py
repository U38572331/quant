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
            viewport={"width": 1600, "height": 900}, # Wider to ensure layout
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        # --- LOGIN CHECK ---
        print("Opening home...")
        page.goto("https://gexstream.com/")
        time.sleep(5)
        
        # Ensure login
        if not (page.locator("text=Logout").is_visible() or page.locator("text=Sign Out").is_visible()):
             print("Not logged in. Logging in...")
             page.goto("https://gexstream.com/login")
             time.sleep(3)
             if page.locator("input[name='email']").is_visible():
                 page.fill("input[name='email']", EMAIL)
                 page.fill("input[name='password']", PASS)
                 page.click("button[type='submit']")
                 page.wait_for_url("**/dashboard**", timeout=15000)
                 print("Login submitted.")
             time.sleep(5)

        # Retrieve Data Function
        extracted_data = {}

        def process_symbol(symbol):
            print(f"--- Processing {symbol} ---")
            
            # Navigate
            # Try searching again as it seemed to work in v5 for navigation
            search = page.locator("input[placeholder*='Search'], input[type='text']").first
            if search.is_visible():
                search.click()
                search.fill(symbol)
                time.sleep(1)
                page.keyboard.press("Enter")
                time.sleep(5)
            else:
                print("Search bar missing, trying direct link...")
                page.goto(f"https://gexstream.com/quote/{symbol}")
                time.sleep(5)

            # Wait for content
            print("Waiting for content to settle...")
            time.sleep(5) # Give it time to render charts/tables
            
            # METHOD 1: ACCESSIBILITY TREE (Great for "visible" text)
            print("Snapshotting Accessibility Tree...")
            try:
                snapshot = page.accessibility.snapshot()
                
                def find_in_node(node, keywords):
                    found = []
                    # Check this node
                    if "name" in node and isinstance(node["name"], str):
                        text = node["name"]
                        if any(k.lower() in text.lower() for k in keywords):
                            found.append(text)
                            # Also grab children as they might contain the value
                            if "children" in node:
                                for child in node["children"]:
                                    if "name" in child:
                                        found.append(f"Child of {text}: {child['name']}")
                    
                    # Recurse
                    if "children" in node:
                        for child in node["children"]:
                            found.extend(find_in_node(child, keywords))
                    return found

                keywords = ["Zero", "Gamma", "Wall", "Net", "Flip", "Call", "Put"]
                matches = find_in_node(snapshot, keywords)
                extracted_data[symbol] = matches
                print(f"Found {len(matches)} accessibility matches.")
            except Exception as e:
                print(f"Accessibility snapshot failed: {e}")
                extracted_data[symbol] = ["Error in snapshot"]

            # METHOD 2: IFRAME DUMP
            print("Checking frames...")
            for frame in page.frames:
                try:
                    title = frame.title()
                    url = frame.url
                    print(f"Frame: {title} ({url})")
                    # innerText of frame
                    text = frame.evaluate("document.body.innerText")
                    if len(text) > 100:
                         # Save snippet if interesting
                         if "gex" in text.lower():
                             print("Found GEX data in frame!")
                             extracted_data[f"{symbol}_frame_{frame.name}"] = text[:500] 
                except: pass

        process_symbol("QQQ")
        process_symbol("SPX")
        
        context.close()
        
        outfile = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\deep_scrape_data.json"
        with open(outfile, "w", encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2)
        print("Done.")

if __name__ == "__main__":
    run()
