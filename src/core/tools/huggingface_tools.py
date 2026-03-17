import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import time
import json

# Load keys from .env in project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, ".env"))

# Check for environmental TOKEN first
HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")

client = InferenceClient(token=HF_TOKEN)

from src.core.tools.gemini_tools import call_gemini

def call_huggingface(system_prompt: str, user_prompt: str, model="meta-llama/Llama-3.3-70B-Instruct", max_retries=3) -> str:
    """
    Standardized wrapper for calling Hugging Face Inference API for LLM tasks.
    Falls back to Gemini if HF is unavailable or credits are depleted.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    if os.getenv("USE_MOCKS") == "true":
        print(f"[LLM] MOCK MODE: Checking prompts...")
        if "Master Evaluator" in system_prompt or "Proposed Video Plan" in user_prompt:
             print("[LLM-Mock] Matched Reflector")
             return "PASS"
        if "Algorithm Reasoning Engine" in system_prompt:
             print("[LLM-Mock] Matched Reasoning Engine")
             if "Two Sum" in user_prompt:
                 return json.dumps({
                     "pattern": "hashmap_hashing",
                     "visual_strategy": "hashmap_grid",
                     "reasoning": "We need to find a complement in O(1) time.",
                     "pseudocode": "for n in nums: if target-n in map: return [map[target-n], i]"
                 })
             return json.dumps({
                 "pattern": "merge_intervals",
                 "visual_strategy": "pointer_motion",
                 "reasoning": "Standard interval merging after sorting.",
                 "pseudocode": "sort, then iterate and merge overlapping windows."
             })
        if "Algorithm Dry Run Engine" in system_prompt:
             print("[LLM-Mock] Matched Dry Run Engine")
             return json.dumps([
                 {"step": 1, "line": "for i, n in enumerate(nums):", "variables": {"i": 0, "n": 2, "diff": 7}, "comment": "Checking 2, complement 7 needed."},
                 {"step": 2, "line": "if diff in prevMap:", "variables": {"i": 0, "n": 2, "prevMap": {}}, "comment": "7 not in map."},
                 {"step": 3, "line": "prevMap[n] = i", "variables": {"i": 0, "n": 2, "prevMap": {2: 0}}, "comment": "Stored 2 at index 0."}
             ])
        if "JSON" in system_prompt or "skeleton" in user_prompt.lower():
             return json.dumps({
                 "title": "Mocked Two Sum",
                 "hook": "Finding pairs",
                 "difficulty": "Easy",
                 "concepts": ["Arrays"],
                 "scenes": [
                     {"scene_id": 1, "chapter": "Intro", "duration_sec": 5, "voiceover": "Hello.", "on_screen_text": "2Sum", "flashcard_concept": "", "visual_plan": "", "code_snippet": "", "highlight_steps": []},
                     {"scene_id": 2, "chapter": "Constraints", "duration_sec": 5, "voiceover": "Constraints", "on_screen_text": "", "flashcard_concept": "", "visual_plan": "", "code_snippet": "", "highlight_steps": []},
                     {"scene_id": 3, "chapter": "Flashcards", "duration_sec": 5, "voiceover": "Flashcards", "on_screen_text": "", "flashcard_concept": "", "visual_plan": "", "code_snippet": "", "highlight_steps": []},
                     {"scene_id": 4, "chapter": "Brute Force", "duration_sec": 5, "voiceover": "Brute", "on_screen_text": "", "flashcard_concept": "", "visual_plan": "", "code_snippet": "", "highlight_steps": []},
                     {"scene_id": 5, "chapter": "Optimal", "duration_sec": 5, "voiceover": "Optimal", "on_screen_text": "", "flashcard_concept": "", "visual_plan": "", "code_snippet": "", "highlight_steps": []},
                     {"scene_id": 6, "chapter": "Line-by-line", "duration_sec": 5, "voiceover": "Line", "on_screen_text": "", "flashcard_concept": "", "visual_plan": "", "code_snippet": "", "highlight_steps": []},
                     {"scene_id": 7, "chapter": "Dry run", "duration_sec": 5, "voiceover": "Dry run", "on_screen_text": "", "flashcard_concept": "", "visual_plan": "", "code_snippet": "", "highlight_steps": []}
                 ],
                 "final_takeaway": "Done.",
                 "cta": "Like and sub."
             })
        if "code" in user_prompt.lower() or "implementation" in user_prompt.lower() or "Coder" in system_prompt:
             if "PREVIOUS COMPILATION FAILED" in user_prompt:
                 print("[LLM-Mock] Returning FIXED code after compiler feedback.")
                 return "```python\ndef solve(): pass\n```"
             else:
                 print("[LLM-Mock] Returning INTENTIONALLY BAD code to test Compiler.")
                 return "```python\ndef solve()::::\n    return ''\n```"
        return "Mocked successful response."

    # Try Hugging Face first with retries for "429 Too Many Requests"
    max_hf_retries = 10
    
    for attempt in range(max_hf_retries):
        try:
            client = InferenceClient(model=model, token=HF_TOKEN)
            
            # We use a massive max_tokens limit of 8192 to allow the LLM to write huge 10-60m video scripts
            response = client.chat_completion(
                messages=messages,
                max_tokens=8192,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] Hugging Face attempt {attempt + 1} failed: {error_msg}")
            
            if "429" in error_msg or "Too Many Requests" in error_msg:
                 wait_time = 65  # free tier hourly quotas often need a long pause
                 print(f"  [HF Quota] Hit rate limit. Sleeping for {wait_time}s before retry...")
                 time.sleep(wait_time)
                 continue
                 
            # If it's a different error (e.g. model disconnected), break out.
            raise e
            
    # If everything fails, return mock if forced
    if os.getenv("FORCE_MOCK_ON_FAIL") == "true":
         print("[LLM] ALL APIs FAILED. Forcing mock response to continue pipeline.")
         return "Mocked response due to API failure."
    raise Exception(f"Hugging Face API completely failed after {max_hf_retries} retries due to strict Rate Limits.")


def generate_huggingface_image(prompt: str, output_path: str, model="black-forest-labs/FLUX.1-schnell"):
    """
    Calls Hugging Face Text-to-Image API to generate cinematic backgrounds.
    """
    print(f"[HF-Image] Generating background for: '{prompt}'...")
    try:
        # Use InferenceClient's text_to_image
        image = client.text_to_image(prompt, model=model)
        image.save(output_path)
        print(f"  [HF-Image] [OK] Saved Image -> {output_path}")
        return output_path
    except Exception as e:
        print(f"  [HF-Image] FAILED: {e}. Falling back to default gradient.")
        return None
