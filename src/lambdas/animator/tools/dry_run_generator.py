"""
Dry Run Generator — Node #3 of the Knowledge Factory.
Generates a step-by-step state trace (JSON) for a specific test case.
"""

import json
import os
import sys
from typing import Dict, Any, List
from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm
from src.prompts.dry_run_prompt import DRY_RUN_SYSTEM_PROMPT, DRY_RUN_USER_PROMPT_TEMPLATE


def dry_run_generator(state: AgentState, input_data: Any = None) -> dict:
    """
    Generates a step-by-step dry run trace for the current problem.
    """
    prob = state.get("problem_data", {}).get("problem", state.get("problem_data", {}))
    title = state.get("problem_title", prob.get("title", "Unknown Problem"))
    
    # Get the latest optimal solution
    # Assuming algorithm_data has the code from a generator node (to be built)
    # For now, let's use the first solution in solutions_data as a fallback
    solutions = state.get("solutions_data", [])
    optimal_code = ""
    if solutions:
        optimal_code = solutions[0].get("content", "")
    
    # Use provided input_data or the first example testcase
    test_cases_raw = prob.get("example_testcases", "No input")
    if not input_data:
        input_data = test_cases_raw
        if "\n" in input_data:
            input_data = input_data.split("\n")[0] # Just the first line

    print(f"[dry_run_generator] Tracing '{title}' for input: {input_data}")

    system_prompt = DRY_RUN_SYSTEM_PROMPT
    user_prompt = DRY_RUN_USER_PROMPT_TEMPLATE.format(
        code=optimal_code,
        test_cases=test_cases_raw # Using the full raw test cases for the prompt
    )
    
    try:
        print(f"  [dry_run_generator] Calling LLM for trace generation...")
        response_text = call_llm(system_prompt, user_prompt)
        
        # Strip potential markdown fences
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        trace = json.loads(response_text)
        
        if not isinstance(trace, list):
             raise ValueError("LLM did not return a list for the dry run trace.")
             
        print(f"  ✓ Generated {len(trace)} steps.")
        
        # Update algorithm_data in state
        algo_data = state.get("algorithm_data", {})
        algo_data["dry_run"] = trace
        algo_data["test_input"] = input_data
        
        return {"algorithm_data": algo_data}
        
    except Exception as e:
        print(f"  [dry_run_generator] Error: {e}")
        return {"error": f"dry_run_generator failed: {e}"}
