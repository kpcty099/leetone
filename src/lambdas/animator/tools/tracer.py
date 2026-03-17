"""
Execution Tracer — Dynamic Dry Run Engine.
Uses sys.settrace to record EXACT variable states at every line
of the algorithm execution. This eliminates all LLM hallucinations
from dry run animations by providing factual ground-truth data.
"""

import sys
import io
import copy
import json
from typing import Any, Dict, List


def _is_safe_value(v: Any) -> bool:
    """Check if a value is JSON-serialisable and safe to snapshot."""
    try:
        json.dumps(v)
        return True
    except (TypeError, ValueError):
        return False


def trace_algorithm(code: str, method_name: str, args: list, max_steps: int = 200) -> List[Dict]:
    """
    Executes `code`, tracing every line inside the method.
    Returns a list of step dicts, each containing:
        {
          "step": int,
          "line_no": int,
          "line_text": str,       # the source line being executed
          "variables": dict,      # snapshot of all primitive local vars
          "is_return": bool       # True if this is the return line
        }
    """
    # Compile the solution class
    namespace: dict = {}
    try:
        exec(compile(code, "<algorithm>", "exec"), namespace)
    except Exception as e:
        return [{"step": 1, "line_no": 0, "line_text": f"# Compile Error: {e}", "variables": {}, "is_return": False}]

    if "Solution" not in namespace:
        return [{"step": 1, "line_no": 0, "line_text": "# No 'Solution' class found.", "variables": {}, "is_return": False}]

    # Split code into lines for line-text lookup
    source_lines = code.splitlines()

    steps: List[Dict] = []
    step_counter = [0]

    def local_tracer(frame, event, arg):
        """Called at every line execution inside the traced method."""
        if event not in ("line", "return"):
            return local_tracer

        if step_counter[0] >= max_steps:
            return None  # Stop tracing

        line_no = frame.f_lineno
        line_text = ""
        if 0 < line_no <= len(source_lines):
            line_text = source_lines[line_no - 1].strip()

        # Snapshot only JSON-safe, non-dunder locals
        raw_locals = frame.f_locals
        safe_vars = {}
        for k, v in raw_locals.items():
            if k.startswith("__"):
                continue
            if k == "self":
                continue
            if _is_safe_value(v):
                safe_vars[k] = copy.deepcopy(v)
            else:
                # Represent complex objects as their string repr (truncated)
                safe_vars[k] = repr(v)[:60]

        step_counter[0] += 1
        steps.append({
            "step": step_counter[0],
            "line_no": line_no,
            "line_text": line_text,
            "variables": safe_vars,
            "is_return": (event == "return"),
        })

        return local_tracer

    def global_tracer(frame, event, arg):
        """Only install local_tracer when we enter the target method."""
        if event == "call" and frame.f_code.co_name == method_name:
            return local_tracer
        return None

    # Run the method under trace
    instance = namespace["Solution"]()
    method = getattr(instance, method_name)

    old_trace = sys.gettrace()
    sys.settrace(global_tracer)
    try:
        if isinstance(args, list):
            method(*args)
        else:
            method(args)
    except Exception as e:
        steps.append({
            "step": step_counter[0] + 1,
            "line_no": -1,
            "line_text": f"# Runtime Error: {e}",
            "variables": {},
            "is_return": True,
        })
    finally:
        sys.settrace(old_trace)

    return steps


def trace_to_file(code: str, method_name: str, args: list, output_path: str = "video_temp/trace.json") -> List[Dict]:
    """Convenience wrapper: trace and save to JSON, returning the steps."""
    import os
    steps = trace_algorithm(code, method_name, args)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(steps, f, indent=2)
    print(f"[execution_tracer] Saved {len(steps)} steps -> {output_path}")
    return steps


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", type=str, default=None, help="Problem slug to trace")
    args_cli = parser.parse_args()

    if args_cli.slug:
        # Load from data/problems/
        path = f"data/problems/{args_cli.slug}/problem.json"
        sol_path = f"data/problems/{args_cli.slug}/solutions.json"
        if os.path.exists(path) and os.path.exists(sol_path):
            with open(path) as f: prob = json.load(f)
            with open(sol_path) as f: sols = json.load(f)
            
            # Find an optimal solution
            code = next((s["code"] for s in sols if s.get("approach") == "optimal"), sols[0]["code"])
            
            # Detect method
            import re
            m = re.search(r"def (\w+)\(self", code)
            method = m.group(1) if m else "solve"
            
            # Parse first test case
            tc_arg = eval(prob["example_testcases"].split("\n")[0])
            if not isinstance(tc_arg, list): tc_arg = [tc_arg]
            
            print(f"Tracing {args_cli.slug} | Method: {method} | Input: {tc_arg}")
            steps = trace_to_file(code, method, tc_arg)
        else:
            print(f"Problem data for '{args_cli.slug}' not found.")
    else:
        # Simple generic test
        test_code = "class Solution:\n    def double(self, x): return x * 2"
        print("Running generic trace test...")
        steps = trace_to_file(test_code, "double", [10])
        print(f"Steps captured: {len(steps)}")
