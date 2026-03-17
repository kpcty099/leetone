"""
LeetCode Problem Scraper — Phase 2
Uses LeetCode's public GraphQL API to fetch all free problems.
Stores each problem in: data/problems/<slug>/problem.json
"""

import os
import json
import time
import requests

GRAPHQL_URL = "https://leetcode.com/graphql"
DATA_DIR = "data/problems"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://leetcode.com/problemset/all/",
}

# GraphQL query to get the full problem list
PROBLEM_LIST_QUERY = """
query questionList($skip: Int, $limit: Int) {
  questionList(
    categorySlug: ""
    limit: $limit
    skip: $skip
    filters: {}
  ) {
    totalNum
    data {
      questionId
      questionFrontendId
      title
      titleSlug
      difficulty
      topicTags { name slug }
      isPaidOnly
      acRate
      status
    }
  }
}
"""

# GraphQL query to get full problem details (anonymous inline format — avoids 400 with named ops)
PROBLEM_DETAIL_QUERY = """
{
  question(titleSlug: "SLUG_PLACEHOLDER") {
    questionId
    questionFrontendId
    title
    titleSlug
    difficulty
    content
    topicTags { name slug }
    exampleTestcases
    isPaidOnly
    hints
    codeSnippets {
      lang
      langSlug
      code
    }
    sampleTestCase
  }
}
"""


def fetch_problem_list(limit=100, skip=0):
    """Fetch a page of problems from LeetCode GraphQL."""
    payload = {
        "query": PROBLEM_LIST_QUERY,
        "variables": {"skip": skip, "limit": limit},
    }
    try:
        r = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        ql = data["data"]["questionList"]
        # Normalize to expected keys
        return {
            "total": ql["totalNum"],
            "questions": ql["data"],
        }
    except Exception as e:
        print(f"  [Scraper] Error fetching page skip={skip}: {e}")
        return None


def fetch_problem_detail(slug: str) -> dict:
    """Fetch full problem statement + constraints for a single problem."""
    query = PROBLEM_DETAIL_QUERY.replace("SLUG_PLACEHOLDER", slug)
    payload = {"query": query}
    try:
        r = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            print(f"  [Scraper] GraphQL errors for {slug}: {data['errors'][0]['message']}")
            return None
        return data["data"]["question"]
    except Exception as e:
        print(f"  [Scraper] Error fetching detail for {slug}: {e}")
        return None


def scrape_all_free_problems(max_problems: int = None):
    """
    Scrapes all free LeetCode problems, saves each to:
    data/problems/<slug>/problem.json
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Step 1: Get total count
    first_page = fetch_problem_list(limit=1, skip=0)
    if not first_page:
        print("[Scraper] Could not reach LeetCode GraphQL. Aborting.")
        return

    total = first_page["total"]
    print(f"[Scraper] Total problems on LeetCode: {total}")

    # Step 2: Paginate through all problems
    all_problems = []
    page_size = 100

    for skip in range(0, total, page_size):
        page = fetch_problem_list(limit=page_size, skip=skip)
        if not page:
            print(f"  [Scraper] Failed at skip={skip}. Retrying in 5s...")
            time.sleep(5)
            page = fetch_problem_list(limit=page_size, skip=skip)
            if not page:
                continue

        for q in page["questions"]:
            if not q.get("isPaidOnly", False):  # Only free problems
                all_problems.append(q)

        print(f"  [Scraper] Fetched {min(skip + page_size, total)}/{total} "
              f"— Free so far: {len(all_problems)}")
        time.sleep(0.8)  # Polite delay

        if max_problems and len(all_problems) >= max_problems:
            break

    print(f"\n[Scraper] Found {len(all_problems)} free problems total.")

    # Step 3: Fetch full details for each problem
    saved = 0
    skipped = 0

    for i, prob in enumerate(all_problems):
        slug = prob["titleSlug"]
        problem_dir = os.path.join(DATA_DIR, slug)
        problem_file = os.path.join(problem_dir, "problem.json")

        # Skip if already scraped
        if os.path.exists(problem_file):
            skipped += 1
            continue

        os.makedirs(problem_dir, exist_ok=True)

        print(f"  [{i+1}/{len(all_problems)}] Fetching detail: {prob['title']}...")
        detail = fetch_problem_detail(slug)
        time.sleep(0.8)

        if not detail:
            print(f"    [SKIP] Could not fetch detail for {slug}")
            continue

        # Parse topic tags
        tags = [t["slug"] for t in (detail.get("topicTags") or [])]

        # Build clean problem record
        record = {
            "id": detail.get("questionFrontendId"),
            "backend_id": detail.get("questionId"),
            "title": detail.get("title"),
            "slug": slug,
            "difficulty": detail.get("difficulty"),
            "tags": tags,
            "ac_rate": prob.get("acRate"),
            "content_html": detail.get("content", ""),
            "example_testcases": detail.get("exampleTestcases", ""),
            "sample_test_case": detail.get("sampleTestCase", ""),
            "hints": detail.get("hints", []),
            "code_snippet_python": next(
                (c["code"] for c in (detail.get("codeSnippets") or [])
                 if c["langSlug"] == "python3"),
                ""
            ),
            "metadata": detail.get("metaData", "{}"),
        }

        with open(problem_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        saved += 1
        if saved % 50 == 0:
            print(f"\n[Scraper] Progress: {saved} saved, {skipped} skipped.\n")

    print(f"\n[Scraper] Done! Saved: {saved} | Skipped (already exist): {skipped}")
    return len(all_problems)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None, help="Max problems to scrape (default: all)")
    args = parser.parse_args()
    scrape_all_free_problems(max_problems=args.max)
