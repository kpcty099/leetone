"""
Animator Node — handles execution tracing and Manim script generation.
Part of the Animator Lambda module.
"""
import os, json, subprocess
from .tools.tracer import trace_to_file

ANIM_DIR = "video_temp/animations"

def animator_node(state: dict) -> dict:
    """
    Animator Node (Agent #2) - Generates Manim scripts and tracers.
    """
    chapters = state.get("chapters", [])
    problem_title = state.get("problem_title", "Unknown")
    solutions_data = state.get("solutions_data", [])
    cache_dir = state.get("cache_dir", "video_temp")
    
    print(f"[animator_node] Processing {len(chapters)} animation segments...")
    
    # 1. Identify optimal code for tracing
    optimal_code = ""
    for sol in solutions_data:
        if sol.get("approach") == "optimal" or "optimal" in sol.get("href", "").lower():
            optimal_code = sol.get("code", "")
            break
    if not optimal_code and solutions_data:
        optimal_code = solutions_data[0].get("code", "")

    # 2. Extract method name for tracer
    method_name = "solve"
    if "def " in optimal_code:
        import re
        match = re.search(r"def (\w+)\(self", optimal_code)
        if match:
            method_name = match.group(1)

    # 3. Perform Execution Trace (Ground Truth)
    trace_path = os.path.join(cache_dir, "trace.json")
    if optimal_code:
        try:
            # We use an example test case input for the trace
            prob_data = state.get("problem_data", {})
            raw_tc = prob_data.get("example_testcases", "[]")
            # Parse first line as input
            import ast
            tc_input = ast.literal_eval(raw_tc.split("\n")[0])
            if not isinstance(tc_input, list): tc_input = [tc_input]

            print(f"  [animator_node] Tracing ground truth for input: {tc_input}")
            trace_to_file(optimal_code, method_name, tc_input, trace_path)
        except Exception as e:
            print(f"  [animator_node] Trace failed: {e}")

    # 4. Update chapters with visual metadata
    updated_chapters = []
    for ch in chapters:
        new_ch = ch.copy()
        # In a real run, we'd call a 'coder' agent or template here
        # For now, we ensure the paths are consistent
        new_ch["anim_script"] = f"{cache_dir}/anim_{new_ch['segment_id']}.py"
        updated_chapters.append(new_ch)
    
    return {"chapters": updated_chapters}
