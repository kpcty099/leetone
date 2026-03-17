"""
Visual Strategy Selector (Node #7) — Mapping Patterns to Visuals.
Decides which reusable visual components to use for each chapter.
"""

from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm

STRATEGY_MAP = {
    "stack": {
        "visual_id": "V_STACK_LIFO",
        "bg_accent": "purple",
        "animation_type": "push_pop"
    },
    "hashmap_hashing": {
        "visual_id": "V_HASH_TABLE",
        "bg_accent": "cyan",
        "animation_type": "key_value_lookup"
    },
    "two_pointers": {
        "visual_id": "V_DOUBLE_POINTER",
        "bg_accent": "green",
        "animation_type": "pointer_shift"
    },
    "sliding_window": {
        "visual_id": "V_WINDOW_SLICE",
        "bg_accent": "orange",
        "animation_type": "window_slide"
    },
    "recursion_tree": {
        "visual_id": "V_TREE_NODES",
        "bg_accent": "red",
        "animation_type": "tree_expand"
    }
}

def strategy_selector_node(state: AgentState) -> dict:
    print(f"[strategy_selector] Assigning visual strategies for '{state['problem_title']}'")
    
    # Get pattern from state or reasoning
    pattern = state.get("pattern", "").lower()
    
    # Fallback to keyword search in reasoning
    if not pattern:
        reasoning = state.get("reasoning", "").lower()
        for key in STRATEGY_MAP.keys():
            if key in reasoning or key.replace("_", " ") in reasoning:
                pattern = key
                break
    
    strategy = STRATEGY_MAP.get(pattern, {
        "visual_id": "V_GENERIC_CODE",
        "bg_accent": "blue",
        "animation_type": "none"
    })
    
    print(f"[strategy_selector] Selected Strategy: {strategy['visual_id']} for pattern '{pattern}'")
    
    # Apply to all chapters that don't have a specific visual plan
    updated_chapters = []
    for ch in state.get("chapters", []):
        new_ch = ch.copy()
        if not new_ch.get("visual_plan"):
            new_ch["visual_id"] = strategy["visual_id"]
            new_ch["bg_accent"] = strategy["bg_accent"]
            new_ch["animation_type"] = strategy["animation_type"]
        updated_chapters.append(new_ch)
        
    return {
        "chapters": updated_chapters, 
        "pattern": pattern,
        "visual_strategy": strategy["visual_id"]
    }

if __name__ == "__main__":
    mock_state = {
        "problem_title": "Valid Parentheses",
        "pattern": "stack",
        "chapters": [{"segment_id": 1, "chapter": "Logic"}]
    }
    res = strategy_selector_node(mock_state)
    print(res)
