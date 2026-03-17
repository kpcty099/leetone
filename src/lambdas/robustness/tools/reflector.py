from typing import List
from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm
from src.core.guardrails import validate_video_plan

def reflector_node(state: AgentState) -> dict:
    print(f"[reflector_node] Critiquing generated plan...")
    
    plan_json = state.get("current_plan_json", "")
    if not plan_json:
        return {"error": "No plan to reflect on."}
        
    # 1. Structural/Schema Guardrails Check (Deterministic)
    is_valid, error_msg, parsed_plan = validate_video_plan(plan_json)
    
    if not is_valid:
         print(f"[reflector_node] Schema validation failed: {error_msg}")
         feedback = state.get("reflection_feedback", [])
         # We need a new list instance to properly trigger LangGraph state updates
         new_feedback = list(feedback)
         new_feedback.append(f"[SCHEMA ERROR] {error_msg}")
         return {
             "parsed_plan": None, 
             "reflection_feedback": new_feedback,
             "retry_count": state.get("retry_count", 0) + 1
         }
         
    # 2. LLM Critique (Semantic Quality)
    # We use a rigorous 70B model to evaluate the depth and pedagogy
    system_prompt = """You are a strict Master Evaluator.
Evaluate the provided JSON video plan for an elite algorithmic explainer video.
Look for:
1. Is the explanation tailored to a middle-school student? Does it use analogies and extremely clear logic?
2. Does it contain a "Line-by-Line Code Breakdown" after the Optimal Solution?
3. Does the "Dry Run" chapter trace variables explicitly element-by-element (e.g. i=0, target=9)?
4. Is the script deep enough to easily last 10-20+ minutes? Ensure Voiceover strings are highly detailed.

If it meets ALL these strict criteria, reply EXACTLY with the word: PASS
If it fails ANY criteria, list the failures so the Planner can revise the draft."""

    try:
        # Pushed to 70B for strong pedagogical evaluation
        critique = call_llm(system_prompt, f"Plan to critique:\n{plan_json}", model="meta-llama/Llama-3.3-70B-Instruct")
        
        if "PASS" in critique.strip().upper():
            print("[reflector_node] [SUCCESS] Quality Check PASSED: Elite Pedagogical standard met.")
            return {
                "parsed_plan": parsed_plan,
                "error": "" # Clear error to proceed
            }
        else:
            print(f"[reflector_node] [FAILED] Quality Check FAILED. Reporting to Master Planner:\n{critique}")
            feedback = state.get("reflection_feedback", [])
            new_feedback = list(feedback)
            new_feedback.append(f"[CONTENT CRITIQUE] {critique}")
            return {
                 "parsed_plan": None, 
                 "reflection_feedback": new_feedback,
                 "retry_count": state.get("retry_count", 0) + 1
            }
    except Exception as e:
        return {"error": f"Reflector failed: {str(e)}"}
