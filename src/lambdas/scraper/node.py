"""
Scraper Node — loads problem data from local disk or captures it autonomously.
Part of the Scraper Lambda module.
"""
import os, json, re
from .tools.screenshot import capture_leetcode_description

DATA_DIR = "data/problems"

def _title_to_slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

def _resolve_slug(problem_input: str) -> tuple[str, str]:
    stripped = problem_input.strip()
    if stripped.isdigit():
        target_id = stripped
        if os.path.isdir(DATA_DIR):
            for slug in os.listdir(DATA_DIR):
                pfile = os.path.join(DATA_DIR, slug, "problem.json")
                if os.path.exists(pfile):
                    with open(pfile, encoding="utf-8") as f:
                        data = json.load(f)
                    if str(data.get("id", "")) == target_id or \
                       str(data.get("backend_id", "")) == target_id:
                        return slug, data.get("title", slug)
        return f"problem-{target_id}", f"Problem {target_id}"
    slug = _title_to_slug(stripped)
    return slug, stripped

def scraper_node(state: dict) -> dict:
    problem_input = state.get("problem_input", state.get("problem_title", "Two Sum"))
    slug, title = _resolve_slug(problem_input)

    print(f"[scraper_node] Loading: '{title}' (slug: {slug})")

    problem_dir = os.path.join(DATA_DIR, slug)
    problem_file = os.path.join(problem_dir, "problem.json")
    solutions_file = os.path.join(problem_dir, "solutions.json")

    problem_data = {}
    solutions_data = []

    if os.path.exists(problem_file):
        with open(problem_file, encoding="utf-8") as f:
            problem_data = json.load(f)
    else:
        # Autonomous scraping could be triggered here if missing
        print(f"  [scraper_node] WARNING: No problem.json at {problem_file}")

    regenerate = state.get("regenerate", False)
    cache_dir = os.path.join(problem_dir, "cache")
    chapters = []

    if regenerate:
        print(f"  [scraper_node] Regenerating: clearing existing cache dir -> {cache_dir}")
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir, ignore_errors=True)
        os.makedirs(cache_dir, exist_ok=True)
    else:
        os.makedirs(cache_dir, exist_ok=True)
        plan_path = os.path.join(cache_dir, "plan.json")
        if os.path.exists(plan_path):
            try:
                with open(plan_path, encoding="utf-8") as f:
                    chapters = json.load(f)
            except Exception:
                pass

    # Redirect logs
    try:
        from src.core.tools.progress_tracker import set_log_path
        set_log_path(cache_dir)
    except Exception:
        pass
    
    if chapters:
        print(f"  [scraper_node] CACHE HIT -- {len(chapters)} chapters loaded.")

    if os.path.exists(solutions_file):
        with open(solutions_file, encoding="utf-8") as f:
            solutions_data = json.load(f)

    # Autonomous Capture
    screenshot_path = os.path.join(problem_dir, "problem_screenshot.png")
    if not os.path.exists(screenshot_path):
        print(f"  [scraper_node] Missing screenshot. Attempting autonomous capture...")
        try:
            capture_leetcode_description(slug, screenshot_path)
        except Exception as e:
            print(f"  [scraper_node] Screenshot capture failed: {e}")

    problem_image_path = os.path.abspath(screenshot_path) if os.path.exists(screenshot_path) else ""

    return {
        "problem_title": problem_data.get("title", title),
        "problem_slug": slug,
        "difficulty": problem_data.get("difficulty", state.get("difficulty", "Medium")),
        "problem_data": problem_data,
        "solutions_data": solutions_data,
        "problem_image_path": problem_image_path,
        "cache_dir": cache_dir,
        "chapters": chapters,
        "error": "",
    }
