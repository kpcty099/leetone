import os
from src.core.state import AgentState
from src.lambdas.renderer.tools.video_renderer import CinematicRenderer

def director_node(state: AgentState) -> dict:
    print(f"[director_node] Initiating cinematic rendering engine for '{state['problem_title']}'...")
    
    plan = state.get("parsed_plan")
    if not plan:
         return {"error": "Director node called without a valid parsed plan."}
         
    problem_slug = state['problem_title'].lower().replace(' ', '_')
    output_dir = f"output/{problem_slug}_temp"
    final_vid_path = f"output/{problem_slug}_final_output.mp4"
    
    # We substitute the general code snippet with the actual generated code if available
    code_snippets = state.get("code_snippets", {})
    if code_snippets and code_snippets.get("full_implementation"):
         print("[director_node] Injecting Coder's optimal implementation into the dry run scene.")
         for scene in plan.get("scenes", []):
              if "run" in scene.get("chapter", "").lower() or "optimal" in scene.get("chapter", "").lower():
                  # Avoid overriding if already highly specific, but usually planner puts pseudo-code
                  scene["code_snippet"] = code_snippets["full_implementation"]
    
    try:
        renderer = CinematicRenderer(plan, output_dir)
        renderer.render(final_vid_path)
        print(f"[director_node] Successfully rendered 10k style cinematic video at {final_vid_path}")
        return {
             "final_video_plan": plan, 
             "error": ""
        }
    except Exception as e:
        return {"error": f"Video rendering failed: {str(e)}"}
