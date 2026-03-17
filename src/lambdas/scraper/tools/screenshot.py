import os
import time
from playwright.sync_api import sync_playwright

def capture_leetcode_description(slug, output_path):
    """
    Independent helper to capture LeetCode description.
    """
    url = f"https://leetcode.com/problems/{slug}/description/"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Larger viewport for higher quality "full screen" feel
        context = browser.new_context(viewport={'width': 1920, 'height': 2000})
        page = context.new_page()
        
        print(f"  [capture] Navigating to {url}")
        page.goto(url, wait_until="networkidle")
        
        # Wait for description to load
        try:
            selector = 'div[data-track-load="description_content"]'
            page.wait_for_selector(selector, timeout=12000)
            
            # ── Full Screen "Optimization": Hide headers, navbars, and side panels ──
            page.evaluate('''() => {
                // Hide header/nav if they exist to isolation the "full screen" content
                const toHide = [
                    '#navbar', 'nav', 'header', '.navbar', 
                    '[data-track-load="header"]', 
                    '.side-panel', '.split-pane-right'
                ];
                toHide.forEach(s => {
                    document.querySelectorAll(s).forEach(el => el.style.display = 'none');
                });
                
                // Ensure the description takes priority
                const el = document.querySelector('div[data-track-load="description_content"]');
                if (el) {
                    el.scrollIntoView();
                    // Optional: remove padding/margin for a "tighter" crop
                    el.style.padding = '40px';
                    el.style.background = '#1a1a1a'; // Match dark theme
                }
            }''')
            time.sleep(3) # Wait for layout settles
            
            element = page.query_selector(selector)
            if element:
                element.screenshot(path=output_path)
                print(f"  [capture] High-fidelity full-screen screenshot saved: {output_path}")
                return True
        except Exception as e:
            print(f"  [capture] Failed to find description selector: {e}")
            page.screenshot(path=output_path)
            return True
        finally:
            browser.close()
    return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        capture_leetcode_description(sys.argv[1], sys.argv[2])
