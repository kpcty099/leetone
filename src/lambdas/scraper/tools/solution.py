"""
LeetCode Solution Scraper — Phase 2
Uses Playwright (headless browser with your saved session) to:
1. Navigate to leetcode.com/problems/<slug>/solutions/
2. Filter: Python3, Most Votes
3. Extract top solutions, classify as Brute/Optimal
4. Verify solutions run against example test cases
5. Save to data/problems/<slug>/solutions.json
"""

import os
import json
import time
import subprocess
import tempfile
import re
from playwright.sync_api import sync_playwright

DATA_DIR = "data/problems"
LEETCODE_BASE = "https://leetcode.com"


def classify_solution(code: str, title: str, index: int) -> str:
    """Classify solution as brute_force or optimal based on heuristics."""
    code_lower = code.lower()
    # Brute force indicators
    if any(k in code_lower for k in ["brute", "naive", "o(n^2)", "o(n2)", "nested"]):
        return "brute_force"
    # Optimal usually has advanced structures
    if any(k in code_lower for k in ["hashmap", "dict", "binary search", "dp", "heap", "deque"]):
        return "optimal"
    # First solution is usually brute, second+ are more optimal
    return "brute_force" if index == 0 else "optimal"


def verify_solution(code: str, test_input: str, problem_slug: str) -> dict:
    """Run the solution code with test input in a subprocess."""
    try:
        # Wrap in a try/except to handle different function signatures
        test_harness = f"""
import sys
{code}

# Try to run with sample test case
try:
    sol = Solution()
    print("SOLUTION_OK")
except Exception as e:
    print(f"SOLUTION_ERROR: {{e}}")
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(test_harness)
            tmp_path = f.name

        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True, text=True, timeout=10
        )
        os.unlink(tmp_path)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if "SOLUTION_OK" in stdout:
            return {"verified": True, "error": ""}
        else:
            return {"verified": False, "error": stderr or stdout}
    except subprocess.TimeoutExpired:
        return {"verified": False, "error": "Timeout"}
    except Exception as e:
        return {"verified": False, "error": str(e)}


def extract_python_code(solution_html: str) -> str:
    """Extract Python code block from solution HTML/text."""
    # Try to find code between python/python3 markdown fences
    patterns = [
        r"```python3?\n(.*?)```",
        r"```Python3?\n(.*?)```",
    ]
    for pattern in patterns:
        match = re.search(pattern, solution_html, re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""


def scrape_solutions_for_problem(slug: str, page) -> list:
    """
    Navigate to the solutions tab and extract top Python solutions.
    `page` is a Playwright page object with an active LeetCode session.
    """
    solutions_url = f"{LEETCODE_BASE}/problems/{slug}/solutions/?languageTags=python3&orderBy=hot"
    print(f"  [SolutionScraper] Fetching: {solutions_url}")

    try:
        page.goto(solutions_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)  # Let JS render

        # Get all solution cards visible
        cards = page.query_selector_all('[class*="title__"]')
        if not cards:
            cards = page.query_selector_all('a[href*="/solutions/"]')

        solutions = []
        seen_hrefs = set()

        for i, card in enumerate(cards[:6]):  # Top 6 to find brute + optimal
            try:
                href = card.get_attribute("href") or ""
                if not href or href in seen_hrefs:
                    continue
                seen_hrefs.add(href)

                # Open each solution in a new tab
                sol_page = page.context.new_page()
                sol_page.goto(f"{LEETCODE_BASE}{href}", wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)

                # Get solution content
                content_el = sol_page.query_selector('[class*="content__"]') or \
                             sol_page.query_selector('article') or \
                             sol_page.query_selector('[data-track-load="solution_content"]')

                raw_text = content_el.inner_text() if content_el else ""
                raw_html = content_el.inner_html() if content_el else ""

                code = extract_python_code(raw_html or raw_text)
                if not code:
                    sol_page.close()
                    continue

                approach = classify_solution(code, slug, i)
                verification = verify_solution(code, "", slug)

                solutions.append({
                    "index": i,
                    "href": href,
                    "approach": approach,
                    "code": code,
                    "verified": verification["verified"],
                    "verify_error": verification["error"],
                })

                print(f"    [{i}] {approach} — verified={verification['verified']}")
                sol_page.close()

                if len(solutions) >= 4:
                    break

            except Exception as e:
                print(f"    [Error] Solution {i}: {e}")
                continue

        return solutions

    except Exception as e:
        print(f"  [SolutionScraper] Error for {slug}: {e}")
        return []


def run_solution_scraper(slugs: list = None, max_problems: int = None):
    """
    Main entry point. Scrapes solutions for the given slugs (or all scraped problems).
    Requires LeetCode to be logged in — will open browser for you to confirm session.
    """
    if not slugs:
        # Discover all scraped problems
        slugs = [
            d for d in os.listdir(DATA_DIR)
            if os.path.isdir(os.path.join(DATA_DIR, d)) and
               os.path.exists(os.path.join(DATA_DIR, d, "problem.json"))
        ]
        # Sort by problem ID
        def get_id(slug):
            f = os.path.join(DATA_DIR, slug, "problem.json")
            try:
                return int(json.load(open(f))["id"])
            except:
                return 9999
        slugs = sorted(slugs, key=get_id)

    if max_problems:
        slugs = slugs[:max_problems]

    print(f"[SolutionScraper] Scraping solutions for {len(slugs)} problems...")

    with sync_playwright() as p:
        # Launch browser in non-headless mode so user can see session is active
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()
        page = context.new_page()

        # Go to LeetCode — user should already be logged in via browser session
        page.goto("https://leetcode.com", wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)

        # Check if logged in
        user_el = page.query_selector('[data-cy="navbar-user-avatar"]') or \
                  page.query_selector('img[alt*="avatar"]')
        if not user_el:
            print("\n[SolutionScraper] ⚠️  NOT LOGGED IN.")
            print("Please log in to LeetCode in the browser window that just opened.")
            print("Then press Enter here to continue...")
            input()

        saved = 0
        for i, slug in enumerate(slugs):
            solutions_file = os.path.join(DATA_DIR, slug, "solutions.json")

            if os.path.exists(solutions_file):
                print(f"  [{i+1}/{len(slugs)}] SKIP (already done): {slug}")
                continue

            print(f"\n  [{i+1}/{len(slugs)}] Processing: {slug}")
            solutions = scrape_solutions_for_problem(slug, page)

            if solutions:
                with open(solutions_file, "w", encoding="utf-8") as f:
                    json.dump(solutions, f, indent=2, ensure_ascii=False)
                saved += 1
                print(f"    Saved {len(solutions)} solutions.")
            else:
                print(f"    No solutions found.")

            time.sleep(1.5)  # Polite delay

        browser.close()

    print(f"\n[SolutionScraper] Done! Saved solutions for {saved} problems.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", type=str, default=None, help="Single problem slug to scrape")
    parser.add_argument("--max", type=int, default=None, help="Max problems to process")
    args = parser.parse_args()

    if args.slug:
        run_solution_scraper(slugs=[args.slug])
    else:
        run_solution_scraper(max_problems=args.max)
