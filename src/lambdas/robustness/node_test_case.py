"""
Test Case Generator Node — analyzing constraints & edge cases via LLM.
"""
import json
from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm

TEST_CASE_PROMPT = """
You are a LeetCode Test Engineer. Analyze the provided problem statement and constraints.
Generate a list of exactly 5 critical test cases:
1. Standard case (Normal input)
2. Minimal case (Smallest possible valid input)
3. Maximal case (Large/Boundary input)
4. Edge case A (e.g., negative numbers, empty array, duplicates)
5. Edge case B (e.g., specific constraint violation check)

Return ONLY a JSON list of objects:
[
  {
    "name": "Small description",
    "input": "raw_input_string_compatible_with_eval",
    "expected": "expected_output_literal",
    "is_edge": true/false
  }
]
"""

def test_case_node(state: AgentState) -> dict:
    prob = state.get("problem_data", {}).get("problem", state.get("problem_data", {}))
    title = state.get("problem_title", "Unknown")
    content = prob.get("content_html", "")
    
    print(f"[test_case_node] Analyzing edge cases for '{title}'...")
    
    user_prompt = f"Problem: {title}\nContent: {content[:2000]}"
    
    try:
        response = call_llm(TEST_CASE_PROMPT, user_prompt)
        
        # Clean JSON markdown
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
            
        test_cases = json.loads(json_str)
        print(f"  [OK] Generated {len(test_cases)} AI test cases.")
        
        # Merge with existing algorithm_data if present
        algo_data = state.get("algorithm_data", {})
        algo_data["ai_test_cases"] = test_cases
        
        return {"algorithm_data": algo_data}
        
    except Exception as e:
        print(f"  [test_case_node] WARNING: LLM test generation failed: {e}")
        return {}
