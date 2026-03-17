"""
Semantic Engine (Node #6) — Cinematic Script Expansion.
Uses OpenAI GPT-4o to transform technical reasoning/dry-runs into 
professional, high-quality educational voiceovers.
"""

import os
import json
from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm
from src.prompts.semantic_prompt import SEMANTIC_SYSTEM_PROMPT, SEMANTIC_USER_PROMPT_TEMPLATE

def semantic_engine_node(state: AgentState) -> dict:
    print(f"[semantic_engine] Enhancing script with GPT-4o for '{state['problem_title']}'")
    
    # 1. Try to load verified knowledge
    slug = state.get("problem_slug", "unknown")
    kb_path = f"data/problems/{slug}/algorithm_data.json"
    
    verified_data = {}
    if os.path.exists(kb_path):
        with open(kb_path, "r") as f:
            verified_data = json.load(f)
            print(f"[semantic_engine] Loaded verified knowledge from {kb_path}")

    # 2. Build the expansion prompt
    system_prompt = SEMANTIC_SYSTEM_PROMPT
    user_prompt = SEMANTIC_USER_PROMPT_TEMPLATE.format(
        problem_title=state['problem_title'],
        reasoning=verified_data.get('reasoning', state.get('reasoning', '')),
        pattern=verified_data.get('pattern', 'General'),
        chapters_json=json.dumps(state.get('chapters', []), indent=2)
    )
    
    try:
        response = call_llm(system_prompt, user_prompt)
        # Clean potential markdown
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            line_parts = response.split("```")
            if len(line_parts) >= 3:
                response = line_parts[1].strip()
            else:
                response = response.strip("`").strip()

        try:
            updated_chapters = json.loads(response)
            # If LLM wrapped it in a dict, extract it
            if isinstance(updated_chapters, dict):
                if "chapters" in updated_chapters:
                    updated_chapters = updated_chapters["chapters"]
                elif len(updated_chapters) == 1:
                    # Take the first key's value if it's a list
                    first_val = list(updated_chapters.values())[0]
                    if isinstance(first_val, list):
                        updated_chapters = first_val
            
            if not isinstance(updated_chapters, list):
                print(f"[semantic_engine] WARNING: Expected list, got {type(updated_chapters)}")
                return {"chapters": state.get("chapters", [])}

            print(f"[semantic_engine] Successfully enhanced {len(updated_chapters)} chapters.")
            return {"chapters": updated_chapters}
        except Exception as json_err:
            print(f"[semantic_engine] JSON Parse Error: {json_err}\nResponse was: {response}")
            return {"chapters": state.get("chapters", [])}
    except Exception as e:
        print(f"[semantic_engine] ERROR: {e}")
        return {"error": f"Semantic Engine failed: {str(e)}"}

if __name__ == "__main__":
    # Smoke test
    mock_state = {
        "problem_title": "Two Sum",
        "problem_slug": "two-sum",
        "chapters": [{"segment_id": 1, "chapter": "Intro", "voiceover": "Let's solve two sum."}]
    }
    # Ensure providers.py is set to openai or huggingface
    res = semantic_engine_node(mock_state)
    print(json.dumps(res, indent=2))
