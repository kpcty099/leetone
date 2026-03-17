"""
Motion Choreographer (Node #8) — Easing & Camera Rules.
Injects metadata for the renderer to perform smooth zooms and pans.
"""

from src.core.state import AgentState

def motion_choreographer_node(state: AgentState) -> dict:
    print(f"[motion_choreographer] Injecting motion metadata for '{state['problem_title']}'")
    
    chapters = state.get("chapters", [])
    updated_chapters = []
    
    for i, ch in enumerate(chapters):
        new_ch = ch.copy()
        
        # Default motion profile
        motion = {
            "zoom": 1.0,
            "pan": (0, 0),
            "easing": "ease_in_out",
            "camera_shake": False
        }
        
        # Chapter-specific motion heuristics
        chapter_name = new_ch.get("chapter", "").lower()
        
        if "intro" in chapter_name:
            motion["zoom"] = 1.05  # Slight Ken Burns zoom
        elif "dry run" in chapter_name or "line-by-line" in chapter_name:
            motion["zoom"] = 1.15  # Focus on the code/stack
            motion["pan"] = (50, 0) # Pan slightly to the right for values
        elif "optimal" in chapter_name:
            motion["zoom"] = 1.1   # Subtle zoom on the solution
            
        new_ch["motion"] = motion
        updated_chapters.append(new_ch)
        
    return {"chapters": updated_chapters}

if __name__ == "__main__":
    mock_state = {
        "problem_title": "Two Sum",
        "chapters": [{"chapter": "Intro"}, {"chapter": "Dry Run"}]
    }
    res = motion_choreographer_node(mock_state)
    import json
    print(json.dumps(res, indent=2))
