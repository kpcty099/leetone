from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm

def coder_node(state: AgentState) -> dict:
    print(f"[coder_node] Generating executable code snippets for '{state['problem_title']}'")
    
    plan = state.get("parsed_plan")
    if not plan:
         return {"error": "Coder node called without a valid parsed plan."}
         
    system_prompt = """You are a senior algorithmic software engineer.
Provide the pure Python 3 solution for the given algorithmic problem.
You must implement exactly two approaches clearly labeled via comments:
1. A brute force approach
2. An optimal approach

DO NOT include any conversational text. DO NOT wrap the code in markdown blocks like ```python. ONLY output the raw Python code."""

    user_prompt = f"Problem: {state['problem_title']}\nDifficulty: {state.get('difficulty', 'Unknown')}\nRequired Concepts: {', '.join(plan.get('concepts', []))}"
    
    try:
        # Use a strong model for correct algorithmic implementation
        response_text = call_llm(system_prompt, user_prompt, model="meta-llama/Llama-3.1-8B-Instruct")
        
        # Clean up possible markdown fences anyway
        clean_code = response_text.strip()
        if clean_code.startswith("```python"):
            clean_code = clean_code[9:]
        if clean_code.endswith("```"):
            clean_code = clean_code[:-3]
            
        clean_code = clean_code.strip()
        
        return {
             "code_snippets": {
                  "full_implementation": clean_code
             }
        }
    except Exception as e:
        return {"error": f"Coder failed: {str(e)}"}
