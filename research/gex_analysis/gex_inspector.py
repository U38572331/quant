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
        
        # --- LOGIN CHECK ---
        page.goto("https://gexstream.com/")
        time.sleep(5)
        
        # Ensure login
        if not (page.locator("text=Logout").is_visible() or page.locator("text=Sign Out").is_visible()):
             print("Logging in...")
             page.goto("https://gexstream.com/login")
             time.sleep(2)
             if page.locator("input[name='email']").is_visible():
                page.fill("input[name='email']", EMAIL)
                page.fill("input[name='password']", PASS)
                page.click("button[type='submit']")
                page.wait_for_url("**/dashboard**", timeout=15000)
        
        # FORCE DASHBOARD
        page.goto("https://gexstream.com/dashboard")
        time.sleep(5)
        
        print(f"Current URL: {page.url}")
        
        # --- INSPECTION ---
        analysis = []
        
        # 1. Inputs
        analysis.append("--- INPUTS ---")
        inputs = page.query_selector_all("input")
        for i, inp in enumerate(inputs):
            try:
                analysis.append(f"Input {i}: type={inp.get_attribute('type')} placeholder={inp.get_attribute('placeholder')} id={inp.get_attribute('id')} class={inp.get_attribute('class')}")
            except: pass

        # 2. Links that might be symbols
        analysis.append("\n--- LINKS (First 50) ---")
        links = page.query_selector_all("a")
        for i, link in enumerate(links[:50]):
            try:
                href = link.get_attribute('href')
                text = link.inner_text().strip()
                if href and ("quote" in href or "result" in href or "QQQ" in text or "SPX" in text):
                    analysis.append(f"Link {i}: text={text} href={href}")
            except: pass

        # 3. Buttons
        analysis.append("\n--- BUTTONS (First 20) ---")
        btns = page.query_selector_all("button")
        for i, btn in enumerate(btns[:20]):
            try:
                 analysis.append(f"Button {i}: text={btn.inner_text().strip()} class={btn.get_attribute('class')}")
            except: pass
            
        # 4. Dump HTML
        html_content = page.content()
        
        # Save analysis
        with open("C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\page_analysis.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(analysis))
            
        # Save HTML
        with open("C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\dashboard.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        context.close()
        print("Inspection done.")

if __name__ == "__main__":
    run()
