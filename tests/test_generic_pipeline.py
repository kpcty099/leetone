"""
Generic Pipeline Test Suite
============================
Dynamically discovers any problem that has a populated `cache` folder under
`data/problems/<slug>/cache/` and runs a full pipeline invocation for each
one with `regenerate=False` (i.e. pure cache validation, no LLM calls).

Results are saved to:
  data/test_results/test_run_<YYYYMMDD_HHMMSS>.txt

Run via:
  python -m pytest tests/test_generic_pipeline.py -v -s
"""

import os
import sys
import glob
import time
import json
import pytest
from datetime import datetime

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.graph import build_agent_graph

DATA_DIR    = "data/problems"
RESULTS_DIR = "data/test_results"

# ── Timestamp log file ────────────────────────────────────────────────────────
_LOG_FILE = os.path.join(RESULTS_DIR, f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def _log(msg: str):
    """Write a line to both stdout and the timestamped result file."""
    print(msg)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ── Discovery ─────────────────────────────────────────────────────────────────

def get_cached_problems() -> list[str]:
    """Return slugs of problems that have a populated `cache` folder."""
    found = []
    if not os.path.exists(DATA_DIR):
        return found
    for slug in sorted(os.listdir(DATA_DIR)):
        prob_dir  = os.path.join(DATA_DIR, slug)
        cache_dir = os.path.join(prob_dir, "cache")
        if not os.path.isdir(cache_dir):
            continue
        has_plan  = os.path.exists(os.path.join(cache_dir, "plan.json"))
        has_video = bool(glob.glob(os.path.join(cache_dir, "*_final.mp4")))
        if has_plan or has_video:
            found.append(slug)
    return found


CACHED_PROBLEMS = get_cached_problems()

_log(f"\n{'='*60}")
_log(f"  Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
_log(f"  Discovered {len(CACHED_PROBLEMS)} cached problems: {CACHED_PROBLEMS}")
_log(f"{'='*60}\n")


# ── Pytest fixture ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("slug", CACHED_PROBLEMS if CACHED_PROBLEMS else ["__no_cache__"])
def test_pipeline_with_cached_data(slug):
    """
    Validate the pipeline can load and complete using only the local cache
    (no LLM calls, no TTS generation).
    """
    if slug == "__no_cache__":
        _log("  [SKIP] No cached problems found – run the pipeline first.")
        pytest.skip("No cached problems found. Run: python src/main.py --problem 'Two Sum'")

    _log(f"\n  [TEST] {slug}")
    t0 = time.time()

    app = build_agent_graph()
    initial_state = {
        "problem_input":    slug,
        "problem_title":    slug.replace("-", " ").title(),
        "problem_slug":     "",
        "difficulty":       "Medium",
        "regenerate":       False,   # MUST be False – use cache only
        "cache_dir":        "",
        "problem_data":     {},
        "solutions_data":   [],
        "chapters":         [],
        "error":            "",
        "errors":           [],
        "retry_count":      0,
        "stm":              {},
        "final_video_path": "",
        "thumbnail_path":   "",
    }

    final_state = app.invoke(initial_state)
    elapsed     = round(time.time() - t0, 1)
    cache_dir   = final_state.get("cache_dir", "")
    chapters    = final_state.get("chapters", [])
    final_video = final_state.get("final_video_path", "")
    error       = final_state.get("error", "")
    errors      = final_state.get("errors", [])

    # ── Report ────────────────────────────────────────────────────────────────
    status = "PASS" if (not error and final_video and os.path.exists(final_video)) else "FAIL"
    _log(f"  [{status}] {slug}  ({elapsed}s)")
    _log(f"    chapters  : {len(chapters)}")
    _log(f"    cache_dir : {cache_dir}")
    _log(f"    video     : {final_video}")
    if error:
        _log(f"    ERROR     : {error}")
    if errors:
        for i, e in enumerate(errors, 1):
            _log(f"    error[{i}]  : {e}")

    # ── Assertions ────────────────────────────────────────────────────────────
    assert not error,                                   f"Pipeline error: {error}"
    assert len(chapters) > 0,                           "No chapters loaded from cache"
    assert final_video,                                 "final_video_path is empty"
    assert os.path.exists(final_video),                 f"Video file missing: {final_video}"
    assert cache_dir == os.path.join(DATA_DIR, slug, "cache"), \
                                                        f"Unexpected cache_dir: {cache_dir}"


# ── Post-run summary ─────────────────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):
    _log(f"\n{'='*60}")
    _log(f"  Session finished — exit status: {exitstatus}")
    _log(f"  Full results saved to: {_LOG_FILE}")
    _log(f"{'='*60}\n")
