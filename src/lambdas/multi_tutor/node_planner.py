"""
Discussion Planner Node — builds conversation flow for Hard problems.
Generates mentor + student personas and a structured dialogue plan
covering problem exploration, mistakes/corrections, and discovery moments.
"""
import os
from src.lambdas.planner.node import _clean_html, _determine_data_structure, _get_solutions

try:
    from src.core.tools.llm_factory import call_llm
    from src.core.tools.progress_tracker import tracker
    from src.prompts.discussion_prompt import DISCUSSION_VIDEO_GENERATOR_PROMPT
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False


MENTOR_PERSONA = {
    "name": "Alex",
    "voice": "en-US-GuyNeural",      # edge_tts — deep, confident
    "role": "Senior engineer with 8 years of competitive programming",
    "style": "Thinks out loud, poses questions before answering them",
}

STUDENT_PERSONA = {
    "name": "Maya",
    "voice": "en-US-JennyNeural",    # edge_tts — lighter, inquisitive
    "role": "CS grad student, strong fundamentals, misses hidden edge cases",
    "style": "Asks why, challenges assumptions, makes common mistakes",
}


def _build_discussion_plan(title: str, difficulty: str, problem_statement: str,
                            ds: dict, brute_code: str, optimal_code: str,
                            tags: list, examples: str) -> list:
    """
    Build a structured 8-scene discussion plan deterministically.
    Returns a list of scene dicts with mentor/student exchange scripts.
    """
    ds_name = ds["name"]
    ds_reason = ds["reason"]

    scenes = [
        {
            "scene_id": 1,
            "title": "THE PROBLEM",
            "duration_sec": 120,
            "mentor_line": f"Alright, Maya. Today's problem is {title}. Let me read the statement, first.",
            "student_line": "Okay. I skimmed it. My first instinct is to try every combination? Like a brute force?",
            "mentor_response": "That's exactly right. Let's trace why that fails, and then we'll fix it.",
            "visual_cue": "problem_statement",
            "is_problem_statement": True,
            "on_screen_text": problem_statement,
            "highlight_steps": ["Read problem carefully", "Identify constraints"],
        },
        {
            "scene_id": 2,
            "title": "THE INSIGHT",
            "duration_sec": 240,
            "mentor_line": f"So, brute force is too slow. But, what if we already know two of the values?",
            "student_line": "Oh! If I fix the first two, the third is determined! I can just look it up!",
            "mentor_response": f"Exactly. And the data structure that gives O(1) lookups is a {ds_name}. {ds_reason}",
            "visual_cue": "insight_moment",
            "is_data_structure_insight": True,
            "highlight_steps": [f"Fix first element", f"Use {ds_name} for O(1) lookup", "Match DS to operation"],
        },
        {
            "scene_id": 3,
            "title": "OPTIMAL SOLUTION",
            "duration_sec": 300,
            "mentor_line": "Let's look at the optimal solution. Watch the pointers closely.",
            "student_line": "Okay. We initialize the structure. Then, we iterate through, checking for the complement.",
            "mentor_response": "Perfect. And paying attention to edge cases makes this completely bulletproof.",
            "visual_cue": "dry_run_animation",
            "is_optimal_code": True,
            "is_dry_run": True,
            "highlight_steps": ["Initialize structure", "Iterate and check complement", "Handle edge cases carefully"],
            "code": optimal_code,
        },
        {
            "scene_id": 4,
            "title": "TAKEAWAYS",
            "duration_sec": 120,
            "mentor_line": f"Final question Maya. What is the complexity?",
            "student_line": f"It is O(n²) time. And space is O(n) for the {ds_name}?",
            "mentor_response": f"Exactly right. The key pattern is to fix one element, reduce to a subproblem, and solve with {ds_name}. Great job.",
            "visual_cue": "flashcard_recap",
            "is_complexity_analysis": True,
            "highlight_steps": [f"Time: O(n²)", f"Space: O(n)", "Pattern: Fix-one, solve subproblem"],
        },
    ]
    return scenes


def discussion_planner_node(state: dict) -> dict:
    """
    LangGraph node: build multi-tutor discussion plan for Hard problems.
    """
    prob = state.get("problem_data", {}).get("problem", state.get("problem_data", {}))
    title = state.get("problem_title", prob.get("title", "Unknown"))
    difficulty = state.get("difficulty", "Hard")
    tags_raw = prob.get("tags", [])
    tags = [t if isinstance(t, str) else t.get("slug", "") for t in tags_raw]

    content_html = prob.get("content_html", "")
    problem_statement = _clean_html(content_html)[:2000]
    examples = prob.get("example_testcases", "")
    code_snippet = prob.get("code_snippet_python", "")

    solutions_data = state.get("solutions_data", [])
    brute_code, optimal_code = _get_solutions(solutions_data, code_snippet)
    ds = _determine_data_structure(tags)

    ds_text = f"{ds['name']} — {ds['reason']}"

    print(f"[discussion_planner] Building discussion plan for '{title}' ({difficulty})")
    print(f"  Mentor: {MENTOR_PERSONA['name']} | Student: {STUDENT_PERSONA['name']}")
    print(f"  Data Structure: {ds['name']}")

    scenes = []
    if _HAS_LLM:
        try:
            print(f"[discussion_planner] Triggering OpenAI to dynamically script dialogue for '{title}'...")
            prompt = (
                f"Problem: {title} ({difficulty})\n"
                f"Data Structure Insight: {ds_text}\n"
                f"Bruteforce Code snippet (if any): {brute_code[:1000]}\n"
                f"Optimal Code snippet (if any): {optimal_code[:1000]}\n"
                f"Mentor Persona: {MENTOR_PERSONA['name']} - {MENTOR_PERSONA['role']}\n"
                f"Student Persona: {STUDENT_PERSONA['name']} - {STUDENT_PERSONA['role']}\n"
            )
            llm_response = call_llm(DISCUSSION_VIDEO_GENERATOR_PROMPT, prompt).strip()
            
            if "```json" in llm_response:
                llm_response = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                parts = llm_response.split("```")
                if len(parts) >= 3:
                    llm_response = parts[1].strip()
            
            raw_scenes = json.loads(llm_response)
            if isinstance(raw_scenes, list):
                for idx, s in enumerate(raw_scenes):
                    scenes.append({
                        "scene_id": s.get("scene_id", idx + 1),
                        "title": s.get("title", f"Scene {idx+1}"),
                        "duration_sec": s.get("duration_sec", 120),
                        "mentor_line": s.get("mentor_line", ""),
                        "student_line": s.get("student_line", ""),
                        "mentor_response": s.get("mentor_response", ""),
                        "on_screen_text": s.get("on_screen_text", ""),
                        "code": s.get("code", ""),
                        "highlight_steps": s.get("highlight_steps", []),
                        "is_problem_statement": s.get("is_problem_statement", False),
                        "is_bruteforce": s.get("is_bruteforce", False),
                        "is_data_structure_insight": s.get("is_data_structure_insight", False),
                        "is_optimal_code": s.get("is_optimal_code", False),
                        "is_dry_run": s.get("is_dry_run", False),
                        "is_complexity_analysis": s.get("is_complexity_analysis", False),
                    })
                print(f"[discussion_planner] GPT-4o wrote {len(scenes)} lively dialogue scenes!")
            else:
                print(f"[discussion_planner] WARNING: LLM returned non-list JSON.")
                scenes = []
        except Exception as e:
            print(f"[discussion_planner] LLM planner failed ({e}), falling back to rigid python template.")
            scenes = []

    if not scenes:
        scenes = _build_discussion_plan(
            title, difficulty, problem_statement,
            ds, brute_code, optimal_code, tags, examples
        )

    # Convert scenes into ChapterData-compatible format
    chapters = []
    for scene in scenes:
        # Combine voices into single voiceover for TTS (used by multi_tts_node to split)
        combined_vo = (
            f"{MENTOR_PERSONA['name']}: {scene.get('mentor_line', '')} "
            f"{STUDENT_PERSONA['name']}: {scene.get('student_line', '')} "
            f"{MENTOR_PERSONA['name']}: {scene.get('mentor_response', '')}"
        )
        chapters.append({
            "segment_id": scene["scene_id"],
            "chapter": scene["title"],
            "duration_sec": scene["duration_sec"],
            "voiceover": combined_vo,
            "on_screen_text": scene.get("on_screen_text", scene["title"]),
            "code_snippet": scene.get("code", ""),
            "highlight_steps": scene.get("highlight_steps", []),
            "flashcard_concept": "",
            "tags": tags,
            "is_problem_statement": scene.get("is_problem_statement", False),
            "is_bruteforce": scene.get("is_bruteforce", False),
            "is_data_structure_insight": scene.get("is_data_structure_insight", False),
            "is_optimal_code": scene.get("is_optimal_code", False),
            "is_dry_run": scene.get("is_dry_run", False),
            "is_complexity_analysis": scene.get("is_complexity_analysis", False),
            "audio_path": None,
            "animation_path": None,
            "video_path": None,
            "mentor_line": scene["mentor_line"],
            "student_line": scene["student_line"],
            "mentor_response": scene["mentor_response"],
            "visual_cue": scene.get("visual_cue", ""),
            "is_problem_statement": scene.get("is_problem_statement", False),
            "is_bruteforce": scene.get("is_bruteforce", False),
            "is_data_structure_insight": scene.get("is_data_structure_insight", False),
            "is_optimal_code": scene.get("is_optimal_code", False),
            "is_dry_run": scene.get("is_dry_run", False),
            "is_complexity_analysis": scene.get("is_complexity_analysis", False),
            "is_discussion": True,
        })

    total_min = sum(c["duration_sec"] for c in chapters) // 60
    print(f"[discussion_planner] ✓ {len(chapters)} scenes planned, ~{total_min} min total")
    return {"chapters": chapters, "error": ""}
