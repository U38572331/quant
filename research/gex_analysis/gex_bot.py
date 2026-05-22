import time
import json
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("Opening gexstream.com...")
        page.goto("https://gexstream.com/")
        
        print("Please log in manually. Waiting for login detection...")
        # Wait for login
        logged_in = False
        while not logged_in:
            try:
                # Check for common post-login indicators
                if (page.locator("text=Logout").is_visible() or 
                    page.locator("text=Sign Out").is_visible() or 
                    "dashboard" in page.url):
                    logged_in = True
                    print("Login detected! Proceeding...")
                else:
                    time.sleep(1)
            except Exception as e:
                time.sleep(1)
        
        # Setup interception
        captured_data = {"qqq": [], "spx": []}
        current_target = None
        
        def handle_response(response):
            try:
                url = response.url.lower()
                # Broad filter for relevant JSON data
                if ("api" in url or "gex" in url or "chart" in url or "data" in url) and "json" in response.headers.get("content-type", ""):
                    try:
                        data = response.json()
                        if current_target:
                            captured_data[current_target].append({
                                "url": response.url,
                                "data": data
                            })
                            print(f"Captured data for {current_target} from {url}")
                    except:
                        pass
            except Exception as e:
                pass

        page.on("response", handle_response)
        
        # Phase 1: QQQ
        current_target = "qqq"
        print("Navigating to QQQ...")
        
        # Try to use the search bar which is typically reliable
        try:
            # Look for a search input
            search_input = page.locator("input[type='text']").first
            if not search_input.is_visible():
                 search_input = page.locator("input[placeholder*='Search']")
            
            if search_input.is_visible():
                print("Found search bar, typing QQQ...")
                search_input.fill("QQQ")
                time.sleep(1)
                page.keyboard.press("Enter")
                # Click the first result if needed, but Enter usually works or shows a dropdown
                time.sleep(2)
                # If a dropdown appears, try to click the first item
                dropdown_item = page.locator(".search-result, .dropdown-item").first
                if dropdown_item.is_visible():
                     dropdown_item.click()
            else:
                print("Search bar not found. Attempting direct URL navigation...")
                page.goto("https://gexstream.com/quote/QQQ")
                
        except Exception as e:
            print(f"Navigation error: {e}")
            print("Please perform QQQ navigation manually if script failed.")

        print("Collecting QQQ data for 10 seconds...")
        time.sleep(10)
        
        # Phase 2: SPX
        current_target = "spx"
        print("Navigating to SPX...")
        
        try:
            search_input = page.locator("input[type='text']").first
            if not search_input.is_visible():
                 search_input = page.locator("input[placeholder*='Search']")

            if search_input.is_visible():
                print("Found search bar, typing SPX...")
                search_input.fill("SPX")
                time.sleep(1)
                page.keyboard.press("Enter")
                time.sleep(2)
                dropdown_item = page.locator(".search-result, .dropdown-item").first
                if dropdown_item.is_visible():
                     dropdown_item.click()
            else:
                print("Search bar not found. Attempting direct URL navigation...")
                page.goto("https://gexstream.com/quote/SPX")
        except Exception as e:
            print(f"Navigation error: {e}")
        
        print("Collecting SPX data for 10 seconds...")
        time.sleep(10)
        
        print("Closing browser...")
        browser.close()
        
        # Save data
        output_file = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\captured_data.json"
        with open(output_file, "w") as f:
            json.dump(captured_data, f, indent=2)
        print(f"Data saved to {output_file}")

if __name__ == "__main__":
    run()
