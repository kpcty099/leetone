"""
Code Executor — Node #2 of the Knowledge Factory.
Verifies and executes generated solutions against test cases.
"""

import sys
import io
import traceback
import time
from typing import List, Dict, Any, Tuple

def execute_leetcode_solution(code: str, method_name: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executes a Python solution class against a list of test cases.
    Each test case should be: {"input": [arg1, arg2], "expected": result}
    """
    results = []
    all_passed = True
    
    # 1. Setup namespace
    namespace = {}
    try:
        exec(code, namespace)
    except Exception as e:
        return {
            "success": False,
            "error": f"Compilation/Import Error: {e}\n{traceback.format_exc()}",
            "results": []
        }
    
    # 2. Extract Solution class
    if "Solution" not in namespace:
        return {
            "success": False,
            "error": "Solution class not found in code.",
            "results": []
        }
    
    solution_cls = namespace["Solution"]
    instance = solution_cls()
    
    if not hasattr(instance, method_name):
        return {
            "success": False,
            "error": f"Method '{method_name}' not found in Solution class.",
            "results": []
        }
    
    method = getattr(instance, method_name)
    
    # 3. Run Test Cases
    for i, tc in enumerate(test_cases):
        args = tc.get("input", [])
        expected = tc.get("expected")
        
        start_time = time.perf_counter()
        try:
            # We assume args is a list [arg1, arg2...]
            if isinstance(args, list):
                actual = method(*args)
            else:
                actual = method(args)
                
            elapsed = (time.perf_counter() - start_time) * 1000 # ms
            
            passed = (actual == expected)
            if not passed:
                all_passed = False
            
            results.append({
                "test_case": i + 1,
                "input": args,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "runtime_ms": round(elapsed, 4)
            })
            
        except Exception as e:
            all_passed = False
            results.append({
                "test_case": i + 1,
                "input": args,
                "expected": expected,
                "actual": f"RUNTIME_ERROR: {e}",
                "passed": False,
                "error_trace": traceback.format_exc()
            })
            
    return {
        "success": all_passed,
        "results": results
    }

if __name__ == "__main__":
    # Internal Test - Generic Example
    test_code = """
class Solution:
    def solve(self, x):
        return x * 2
    """
    cases = [
        {"input": [5], "expected": 10},
        {"input": [21], "expected": 42},
    ]
    
    print("Testing Code Executor with Generic Logic...")
    report = execute_leetcode_solution(test_code, "solve", cases)
    print(f"Success: {report['success']}")
    for r in report['results']:
        print(f"Case {r['test_case']}: {'PASS' if r['passed'] else 'FAIL'} (Actual: {r['actual']})")
