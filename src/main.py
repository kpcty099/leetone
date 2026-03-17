"""
Main entry point for the LeetCode Video Generator.
Usage:
    python src/main.py --problem "Two Sum"
    python src/main.py --problem 1
    python src/main.py --problem "Add Two Numbers"
"""
import os, sys, shutil, argparse, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.graph import build_agent_graph

try:
    from src.core.tools.progress_tracker import tracker
except Exception:
    tracker = None


def run_pipeline(problem_input: str, regenerate: bool = False):
    print(f"\n{'='*60}")
    print(f"  LeetCode Video Generator - MVP")
    print(f"  Problem: {problem_input}")
    print(f"  Regenerate: {regenerate}")
    print(f"{'*'*60}\n")

    # Clean temp dirs (not output — keep previous successful runs)
    # Note: Disabled for 'Valid Parentheses' run to allow resumption of rendering.
    # for d in ["video_temp"]:
    #     if os.path.exists(d):
    #         try:
    #             shutil.rmtree(d)
    #             print(f"[main] Cleared {d}/")
    #         except Exception as e:
    #             print(f"[main] Warning: could not clear {d}: {e}")

    app = build_agent_graph()

    if tracker:
        tracker.start()  # Will be updated when chapters are known

    initial_state = {
        "problem_input":  problem_input,
        "problem_title":  problem_input,
        "problem_slug":   "",
        "difficulty":     "Medium",
        "regenerate":     regenerate,
        "cache_dir":      "",
        "problem_data":   {},
        "solutions_data": [],
        "chapters":       [],
        "error":          "",
        "errors":         [],       # Accumulated errors across all nodes
        "retry_count":    0,        # Max = 3 before forced END
        "stm":            {},       # Short-term memory
        "final_video_path": "",
        "thumbnail_path": "",
    }

    print(f"[main] Invoking graph...")
    final_state = app.invoke(initial_state)
    print(f"[main] Graph invocation complete.")

    if tracker:
        tracker.print_summary()

    # ── Report results ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    video_path = final_state.get("final_video_path", "")
    error      = final_state.get("error", "")
    errors     = final_state.get("errors", [])     # Full accumulated error list
    retries    = final_state.get("retry_count", 0)
    chapters   = final_state.get("chapters", [])

    if video_path and os.path.exists(video_path):
        size_mb = os.path.getsize(video_path) / 1024 / 1024
        dur_min = sum(c.get("duration_sec", 0) for c in chapters) // 60
        
        # Check if this was a fast cache load (no new TTS generation)
        cache_loaded = final_state.get("regenerate") is False and len(chapters) > 0 and chapters[0].get("audio_path")
        
        if cache_loaded:
            print(f"  ✓ FAST CACHE LOAD SUCCESSFUL")
            print(f"  Bypassed LLM generation. Found existing video.")
        else:
            print(f"  ✓ SUCCESS!")
            
        print(f"  Video:     {video_path}")
        thumb = final_state.get("thumbnail_path", "")
        if thumb and os.path.exists(thumb):
            print(f"  Thumbnail: {thumb}")
        print(f"  Size:     {size_mb:.0f} MB")
        print(f"  Chapters: {len(chapters)}")
        print(f"  Duration: ~{dur_min} minutes")
        if errors:
            print(f"  ⚠ Non-fatal warnings ({len(errors)}):")
            for e in errors:
                print(f"    · {e}")
    else:
        print(f"  ✗ Pipeline terminated WITHOUT producing a video.")
        print(f"  Retries attempted: {retries} / 3")
        print()
        if errors:
            print(f"  ─── Error Log ({len(errors)} issues) ───────────────────────")
            for i, e in enumerate(errors, 1):
                print(f"  {i:02d}. {e}")
        elif error:
            print(f"  Last error: {error}")
        else:
            print("  No errors captured — check logs above for details.")
        print()
        print("  ► Next Steps: Review errors above and re-run after fixes.")
        print("  ► Error log also saved to: output/debug_state.json")

    print(f"{'='*60}\n")

    # Save debug state
    try:
        os.makedirs("output", exist_ok=True)
        with open("output/debug_state.json", "w", encoding="utf-8") as f:
            # Serialize only JSON-safe fields
            safe = {k: v for k, v in final_state.items()
                    if k not in ("problem_data", "solutions_data")}
            json.dump(safe, f, indent=2, default=str)
    except Exception:
        pass

    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LeetCode Video Generator")
    parser.add_argument(
        "--problem",
        default="Two Sum",
        help='Problem title ("Two Sum") or number ("1")',
    )
    parser.add_argument(
        "--regenerate",
        type=bool,
        default=False,
        help="Bypass local cache and regenerate new video version.",
    )
    args = parser.parse_args()
    
    # Simple truthy conversion for string bools if passed like --regenerate=True
    is_regen = str(args.regenerate).lower() in ("true", "1", "yes", "t")
    
    run_pipeline(args.problem, regenerate=is_regen)
