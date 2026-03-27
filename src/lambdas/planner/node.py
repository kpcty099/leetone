"""
Planner Node — builds the video plan via dynamic LLM logic or rigid fallback.
Part of the Planner Lambda module.
"""
import os, re, json, html
from src.core.tools.llm_factory import call_llm
from src.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, PLANNER_VIDEO_GENERATOR_PROMPT

DATA_DIR = "data/problems"

def _clean_html(html_str: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_str or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def _get_solutions(solutions_data: list, fallback_snippet: str) -> tuple:
    """Extracts brute and optimal code from solutions data."""
    brute, optimal = "", ""
    for s in solutions_data:
        code = s.get("code", "")
        approach = s.get("approach", "").lower()
        if "bruteforce" in approach or "naive" in approach:
            brute = code
        elif "optimal" in approach or "efficient" in approach:
            optimal = code
    
    if not optimal and solutions_data:
        optimal = solutions_data[0].get("code", "")
    if not optimal:
        optimal = fallback_snippet
    
    return brute, optimal

def _determine_data_structure(tags: list) -> dict:
    """Maps tags to a primary data structure for discussion."""
    ds_map = {
        "hash-table": {"name": "Hash Map", "reason": "to achieve O(1) lookup time"},
        "stack": {"name": "Stack", "reason": "to maintain LIFO order for nested structures"},
        "queue": {"name": "Queue", "reason": "for BFS-like level traversal"},
        "two-pointers": {"name": "Two Pointers", "reason": "to optimize space by traversing in-place"},
        "binary-search": {"name": "Binary Search", "reason": "to reduce time complexity to logarithmic"},
        "dynamic-programming": {"name": "DP Table", "reason": "to cache subproblem results and avoid recomputation"},
    }
    for tag in tags:
        if tag in ds_map:
            return ds_map[tag]
    return {"name": "Array", "reason": "as the primary data storage"}

def planner_node(state: dict) -> dict:
    """
    Planner Node (Agent #1) - Generates the video structural plan.
    """
    problem_title = state.get("problem_title", "Unknown")
    problem_data = state.get("problem_data", {})
    solutions_data = state.get("solutions_data", [])
    
    # ── Logic ────────────────────────────────────────────────────────────
    print(f"[planner_node] Building chapters for '{problem_title}'...")
    
    # Extract problem statement
    content = problem_data.get("content", "")
    content_clean = _clean_html(content)
    
    # Identify snippet
    snippet = ""
    if solutions_data:
        snippet = solutions_data[0].get("code", "")
    
    # Get Pattern (Reasoning)
    from .tools.reasoning import analyze_pattern
    reasoning = analyze_pattern(problem_title, content_clean, snippet)
    pattern = reasoning.get("pattern", "generic")
    
    # Construct LLM Prompt
    system_prompt = PLANNER_SYSTEM_PROMPT
    user_prompt = PLANNER_VIDEO_GENERATOR_PROMPT.format(
        title=problem_title,
        difficulty=state.get("difficulty", "Medium"),
        description=content_clean,
        code=snippet,
        pattern=pattern
    )
    
    try:
        response = call_llm(system_prompt, user_prompt)
        # Attempt to parse JSON
        plan_obj = {}
        try:
            # Enhanced JSON extractor
            clean_res = response.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_res:
                 clean_res = clean_res.split("```")[-1].split("```")[0].strip()
            
            # Remove potential leading/trailing non-JSON noise
            start_idx = clean_res.find("{")
            end_idx = clean_res.rfind("}")
            if start_idx != -1 and end_idx != -1:
                clean_res = clean_res[start_idx:end_idx+1]
                
            plan_obj = json.loads(clean_res)
        except Exception as e:
            print(f"  [planner_node] WARNING: JSON parse failed ({e}). Falling back to generic plan.")
            plan_obj = {
                "scenes": [
                    {"scene_id": "1", "type": "intro", "duration": 15, "voiceover": f"Welcome! Today we're solving {problem_title}."},
                    {"scene_id": "2", "type": "algo", "duration": 45, "voiceover": f"The core idea is using {pattern}."}
                ]
            }

        # 4. Map new schema to AgentState
        scenes = plan_obj.get("scenes", [])
        chapters = []
        for i, s in enumerate(scenes):
            chapters.append({
                "segment_id": i + 1,
                "chapter": s.get("type", "Overview").capitalize(),
                "duration_sec": int(s.get("duration", 60)),
                "voiceover": s.get("voiceover", ""),
                "on_screen_text": s.get("subtitle", ""),
                "code_snippet": plan_obj.get("code", snippet),
                "highlight_steps": s.get("visual_elements", []),
                "flashcard_concept": plan_obj.get("problem_analysis", {}).get("pattern", pattern),
                "tags": [pattern],
                "dry_run_step": s.get("linked_dry_run_step")
            })

        # Save plan and metadata to cache
        cache_dir = state.get("cache_dir")
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            plan_path = os.path.join(cache_dir, "plan.json")
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump(plan_obj, f, indent=2)
            print(f"  [planner_node] Saved 10-phase plan to {plan_path}")

        return {
            "chapters": chapters,
            "problem_analysis": plan_obj.get("problem_analysis"),
            "test_cases": plan_obj.get("test_cases"),
            "dry_run": plan_obj.get("dry_run"),
            "validation": plan_obj.get("validation"),
            "self_reflection": plan_obj.get("self_reflection"),
            "pattern": plan_obj.get("problem_analysis", {}).get("pattern", pattern)
        }

    except Exception as e:
        print(f"  [planner_node] ERROR: {e}")
        return {"error": f"Planner failed: {str(e)}"}
