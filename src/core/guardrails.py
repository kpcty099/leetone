import json
from typing import Dict, Any, Tuple

def validate_video_plan(plan_json: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates the generated JSON plan against schema rules.
    Updated for Phase 2 — 8-chapter canonical structure.
    'visual_plan' is now optional. 'flashcard_concept' replaces flashcard chapter requirement.
    """
    # Extract JSON from potentially fenced markdown
    clean_json = plan_json.strip()
    if "```json" in clean_json:
        clean_json = clean_json.split("```json")[1]
    if "```" in clean_json:
        clean_json = clean_json.split("```")[0]
    clean_json = clean_json.strip()

    try:
        plan = json.loads(clean_json)
    except Exception as e:
        return False, f"Invalid JSON format. Exception: {e}", {}

    # Top-level required fields
    required_fields = ["title", "hook", "difficulty", "concepts", "scenes", "final_takeaway", "cta"]
    for field in required_fields:
        if field not in plan:
            return False, f"Missing required top-level field: '{field}'", {}

    if not isinstance(plan.get("scenes"), list) or len(plan["scenes"]) == 0:
        return False, "The 'scenes' field must be a non-empty array.", {}

    # Validate required chapter types are present
    chapters_found = [scene.get("chapter", "").lower() for scene in plan["scenes"]]
    
    errors = []
    if not any("brute" in c for c in chapters_found):
        errors.append("Missing a 'Brute Force' chapter scene.")
    if not any("optimal" in c or "derivation" in c for c in chapters_found):
        errors.append("Missing an 'Optimal' chapter scene.")
    if not any("dry run" in c or "trace" in c or "run" in c for c in chapters_found):
        errors.append("Missing a 'Dry Run' chapter scene.")
    if not any("constraint" in c or "statement" in c or "problem" in c for c in chapters_found):
        errors.append("Missing a 'Problem Statement' or 'Constraints' chapter scene.")

    if errors:
        return False, " ".join(errors), {}

    # Per-scene field validation (visual_plan is now optional)
    REQUIRED_SCENE_FIELDS = ["scene_id", "chapter", "duration_sec", "voiceover", "on_screen_text"]
    for i, scene in enumerate(plan["scenes"]):
        for field in REQUIRED_SCENE_FIELDS:
            if field not in scene:
                return False, f"Scene {i+1} is missing required field: '{field}'", {}

        if not isinstance(scene["duration_sec"], (int, float)):
            return False, f"Scene {i+1} duration_sec must be a number.", {}

        if scene["duration_sec"] < 3:
            return False, f"Scene {i+1} has invalid duration ({scene['duration_sec']}s). Must be >= 3s.", {}

    return True, "", plan
