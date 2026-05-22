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
            viewport={"width": 1600, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        # --- LOGIN CHECK ---
        page.goto("https://gexstream.com/")
        time.sleep(5)
        
        # --- PROCESS SYMBOL ---
        def extract_state(symbol):
            print(f"--- Extracting State for {symbol} ---")
            
            # Navigate
            page.goto(f"https://gexstream.com/quote/{symbol}")
            time.sleep(10) # Wait for hydration
            
            # SCRIPT INJECTION: Search for common frameworks
            state_dump = page.evaluate("""() => {
                const extraction = {};
                
                // 1. Next.js
                if (window.__NEXT_DATA__) extraction.nextData = window.__NEXT_DATA__;
                
                // 2. Nuxt.js
                if (window.__NUXT__) extraction.nuxtData = window.__NUXT__;
                
                // 3. React Fiber Traversal (Very powerful)
                // Finds the root element and walks the fiber tree to find props "netGex", "zeroGamma", etc.
                function findReactProps(root) {
                    const queue = [root];
                    const found = [];
                    const maxDepth = 1000;
                    let processed = 0;
                    
                    while (queue.length > 0 && processed < maxDepth) {
                        const node = queue.shift();
                        processed++;
                        
                        if (node.memoizedProps) {
                             const p = node.memoizedProps;
                             // Heuristics for data
                             if (p.data || p.gex || p.chartData || p.netGex || p.gamma) {
                                 found.push(p);
                             }
                        }
                        
                        if (node.child) queue.push(node.child);
                        if (node.sibling) queue.push(node.sibling);
                    }
                    return found;
                }

                // Find react root
                // Usually #root, #__next, or #app
                const rootEl = document.getElementById('__next') || document.getElementById('root') || document.getElementById('app');
                if (rootEl) {
                    // Try to get internal React key
                    const key = Object.keys(rootEl).find(k => k.startsWith('__reactContainer') || k.startsWith('__reactFiber'));
                    if (key) {
                        extraction.reactProps = "Found React Root! Traversing...";
                        // Note: We can't return circular structures, so we'd need to simplify.
                        // Let's just return keys for now to see if it works.
                        extraction.reactKeysFound = key;
                    }
                }
                
                // 4. Global Variables Search
                for (const k of Object.keys(window)) {
                    if (k.toLowerCase().includes('gex') || k.toLowerCase().includes('data')) {
                        try {
                            extraction[k] = window[k];
                        } catch(e) {}
                    }
                }
                
                return extraction;
            }""")
            
            return state_dump

        data_qqq = extract_state("QQQ")
        
        context.close()
        
        outfile = "C:\\Users\\user\\.gemini\\antigravity\\scratch\\gex_analysis\\js_state_dump.json"
        with open(outfile, "w", encoding='utf-8') as f:
            json.dump(data_qqq, f, indent=2, default=str)
        print("Done.")

if __name__ == "__main__":
    run()
