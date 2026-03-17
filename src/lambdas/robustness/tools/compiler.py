import ast
from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm

def get_coder_prompt(problem_title, difficulty, concepts, compiler_feedback=""):
    system_prompt = """You are a senior algorithmic software engineer writing code for a video presentation.
Provide the pure Python 3 solution for the given algorithmic problem.
You must implement exactly two approaches clearly labeled via comments:
1. A brute force approach
2. An optimal approach

CRITICAL VISUAL CONSTRAINTS for Video Layout:
- Do not exceed 80 characters per line (it will wrap and look cramped).
- Try to keep the total line count under 30 lines (exclude unnecessary blank lines).

DO NOT include any conversational text. DO NOT wrap the code in markdown blocks like ```python. ONLY output the raw Python code."""

    user_prompt = f"Problem: {problem_title}\nDifficulty: {difficulty}\nRequired Concepts: {', '.join(concepts)}"
    
    if compiler_feedback:
        user_prompt += f"\n\n[PREVIOUS COMPILATION FAILED]\n{compiler_feedback}\nPlease fix the code and ensure it complies with the visual constraints."
        
    return system_prompt, user_prompt

def coder_node(state: AgentState) -> dict:
    """Agent 1 (Coder): Writes the code/UI logic."""
    print(f"[coder_node] Generating executable code snippets for '{state['problem_title']}'")
    
    plan = state.get("parsed_plan")
    if not plan:
         return {"error": "Coder node called without a valid parsed plan."}
         
    compiler_feedback = state.get("error", "") if "Compiler" in state.get("error", "") else ""
    
    system_prompt, user_prompt = get_coder_prompt(
        state.get("problem_title"),
        state.get("difficulty", "Unknown"),
        plan.get("concepts", []),
        compiler_feedback
    )
    
    try:
        # Use a strong model for correct algorithmic implementation
        response_text = call_llm(system_prompt, user_prompt, model="meta-llama/Llama-3.1-8B-Instruct")
        
        # Clean up possible markdown fences
        clean_code = response_text.strip()
        if clean_code.startswith("```python"):
            clean_code = clean_code[9:]
        if clean_code.endswith("```"):
            clean_code = clean_code[:-3]
            
        clean_code = clean_code.strip()
        
        return {
             "code_snippets": {
                  "full_implementation": clean_code
             },
             "error": "" # Clear any previous compiler errors if we generated new code
        }
    except Exception as e:
        return {"error": f"Coder failed: {str(e)}"}

def compiler_node(state: AgentState) -> dict:
    """Agent 2 (Compiler): Tries to run the code. Feedback: If it fails or looks 'cramped', sends error back."""
    print(f"[compiler_node] Testing code for visual layout and syntax for '{state['problem_title']}'")
    
    code = state.get("code_snippets", {}).get("full_implementation", "")
    if not code:
        return {"error": "Compiler node called without code."}
        
    errors = []
    
    # 1. Syntax Verification (Headless IDE check)
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"SyntaxError: {str(e)}")
        
    # 2. Visual Constraint Check (Cramped logic)
    lines = code.split("\n")
    max_line_length = max((len(line) for line in lines), default=0)
    
    if max_line_length > 85: # A slightly more forgiving threshold than 80
        errors.append(f"Visual Issue: Code is too wide ({max_line_length} chars). Video layout will wrap and look cramped. Keep lines under 80 characters.")
        
    num_lines = len(lines)
    if num_lines > 40:
        errors.append(f"Visual Issue: Code is too long ({num_lines} lines). It will not fit comfortably on a single screen without a confusing scroll. Condense logic to under 35 lines.")
        
    if errors:
        feedback_str = "[Compiler Node Feedback]\n" + "\n".join(errors)
        print(feedback_str)
        return {
            "error": feedback_str,
            "retry_count": state.get("retry_count", 0) + 1
        }
        
    print("[compiler_node] Code compiled successfully and passed visual constraints.")
    return {
        "error": "" # Clear error indicating success
    }
