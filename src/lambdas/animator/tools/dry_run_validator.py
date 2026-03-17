import json
from typing import Dict, Any, List
from src.core.state import AgentState

def dry_run_validator(state: AgentState) -> dict:
    """
    Validates the consistency of the dry run trace stored in algorithm_data.
    Checks for structure, logic changes, and final result alignment.
    """
    algo_data = state.get("algorithm_data", {})
    trace = algo_data.get("dry_run", [])
    
    if not trace:
        return {"error": "No dry run trace found to validate."}
    
    print(f"[dry_run_validator] Validating trace with {len(trace)} steps...")
    
    errors = []
    
    # 1. Structural Validation
    for i, step in enumerate(trace):
        step_num = step.get("step")
        if step_num != i + 1:
            errors.append(f"Step sequence mismatch: expected {i+1}, found {step_num}")
        
        required_keys = ["line", "variables", "comment"]
        for key in required_keys:
            if key not in step:
                errors.append(f"Step {step_num} missing required key: '{key}'")

    # 2. Logic Consistency (Basic)
    all_vars = [json.dumps(s.get("variables", {}), sort_keys=True) for s in trace]
    if len(set(all_vars)) == 1 and len(trace) > 1:
        errors.append("Trace variables are static across all steps; likely a hallucination.")

    # 3. Final Result Alignment
    # If the code_executor ran and finished, we should check if the trace ends with the same logic.
    executed_results = algo_data.get("execution_report", {}).get("results", [])
    if executed_results:
        # Assuming the first test case matches the trace
        expected_final = executed_results[0].get("actual")
        final_vars = trace[-1].get("variables", {})
        
        # We check common variable names for the result: 'result', 'ans', 'output', 'return_val'
        found_match = False
        potential_keys = ["result", "ans", "output", "return_val", "indices"]
        for key in potential_keys:
            if final_vars.get(key) == expected_final:
                found_match = True
                break
        
        if not found_match and "return" in trace[-1].get("line", "").lower():
             # If it's a return line but none of our keys matched, it's suspicious but not necessarily an error
             print(f"  [Warning] Trace ends on return but final variable match not found. Expected: {expected_final}")

    if errors:
        print(f"  ✗ Validation failed: {len(errors)} issues found.")
        return {"error": "; ".join(errors)}
    
    print("  ✓ Trace validated successfully.")
    return {"algorithm_data": algo_data}
