"""
Reflection Node — Justifying the output and catching hallucinations.
"""
import json
from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm

REFLECTION_PROMPT = """
You are a Senior Algorithm Architect. Review the following LeetCode solution plan:
1. Problem: {title}
2. Edge Cases identified: {test_cases}
3. Generated Plan (Chapters): {plan_summary}

Tasks:
1. Verify if the proposed logic correctly handles ALL identified edge cases.
2. Provide a 'Justification Score' (0-10).
3. If score < 8, explain exactly what is missing or wrong.

Return ONLY a JSON object:
{
  "score": float,
  "justification": "Why this approach is correct",
  "issues": ["List of problems found"],
  "should_retry": true/false
}
"""

def reflection_node(state: AgentState) -> dict:
    chapters = state.get("chapters", [])
    title = state.get("problem_title", "Unknown")
    algo_data = state.get("algorithm_data", {})
    test_cases = algo_data.get("ai_test_cases", [])
    
    if not chapters:
        return {}

    print(f"[reflection_node] Reviewing plan for '{title}'...")
    
    plan_summary = []
    for c in chapters:
        plan_summary.append({
            "chapter": c['chapter'],
            "voiceover_snippet": c['voiceover'][:200],
            "code_shown": bool(c.get('code_snippet'))
        })

    user_prompt = f"Title: {title}\nTest Cases: {json.dumps(test_cases)}\nPlan Summary: {json.dumps(plan_summary)}"
    
    try:
        response = call_llm(REFLECTION_PROMPT.format(title=title, test_cases=test_cases, plan_summary=plan_summary), user_prompt)
        
        # Clean JSON markdown
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
            
        result = json.loads(json_str)
        print(f"  [Justification Score] {result['score']}/10")
        print(f"  [Reflection] {result['justification']}")
        
        if result.get("issues"):
            for issue in result["issues"]:
                print(f"  [ISSUE] {issue}")
        
        # If retry is flagged, set high-level error to trigger conditional router
        update = {"stm": {**state.get("stm", {}), "reflection": result}}
        
        if result.get("should_retry") and state.get("retry_count", 0) < 2:
            update["error"] = f"Reflection Error: {'; '.join(result['issues'])}"
            print(f"  [RETRACTED] Reflection triggered a retry.")
            
        return update
        
    except Exception as e:
        print(f"  [reflection_node] WARNING: Reflection failed: {e}")
        return {}
