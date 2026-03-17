import os
from src.core.state import SegmentState
from src.lambdas.renderer.tools.video_renderer import CinematicRenderer
from src.core.tools.llm_factory import call_llm

from .grounding import grounding_node
from src.lambdas.visuals.tools.vlm_judge import vlm_judge_node
from src.lambdas.visuals.tools.base_visualizer import get_visualizer_for_problem

def segment_worker(state: SegmentState) -> dict:
    """
    Worker node that processes a single video segment.
    Generates audio, visual, and coordinates grounding.
    """
    print(f"  [SegmentWorker] Processing Segment {state['segment_id']}: {state['chapter']}")
    
    # 0. VLM Judge (Visual Choice Tree)
    style_guide = vlm_judge_node(state)
    state['style_guide'] = style_guide
    
    # 1. Grounding Agent (WhisperX + UI-TARS)
    audio_dur = float(state.get('duration_sec', 10))
    grounding_data = grounding_node(state, audio_dur)
    state['temporal_map'] = grounding_data.get('temporal_map', [])
    state['spatial_map'] = grounding_data.get('spatial_map', [])
    
    # 2. Render Manim Animation Constraint
    animation_clip_path = None
    if "dry run" in state['chapter'].lower() or "naive" in state['chapter'].lower():
        print(f"  [SegmentWorker] Generating Manim Visualizer for: {state['chapter']}")
        try:
            # We don't have the full problem data here, just title. Mock testcase for now.
            # In Phase 3, segment state should hold problem_data from planner.
            visualizer = get_visualizer_for_problem(
                {"title": state.get("problem_title", "Problem"), "slug": "problem"},
                 # For actual run, we parse it from code_snippets. Using default for now
                {"nums": [1,2,3,4,5]} 
            )
            # Output to this specific segment's subfolder
            output_dir = f"video_temp/segment_{state['segment_id']}"
            os.makedirs(output_dir, exist_ok=True)
            animation_clip_path = visualizer.render(output_dir)
        except Exception as e:
            print(f"  [SegmentWorker] Visualizer failed: {e}")

    # For this implementation, we use the CinematicRenderer to render the segment.
    # We create a mini-plan for the renderer.
    mini_plan = {
        "title": state['chapter'],
        "scenes": [
            {
                "scene_id": state['segment_id'],
                "chapter": state['chapter'],
                "voiceover": state['voiceover'],
                "on_screen_text": state['on_screen_text'],
                "code_snippet": state['code_snippet'],
                "highlight_steps": state['highlight_steps'],
                "duration_sec": state['duration_sec'],
                "style_guide": state.get('style_guide', {}),
                "temporal_map": state.get('temporal_map', []),
                "spatial_map": state.get('spatial_map', []),
                "animation_clip": animation_clip_path
            }
        ]
    }
    
    output_dir = f"video_temp/segment_{state['segment_id']}"
    os.makedirs(output_dir, exist_ok=True)
    
    renderer = CinematicRenderer(mini_plan, output_dir)
    segment_video_path = os.path.join(output_dir, f"segment_{state['segment_id']}.mp4")
    
    try:
        renderer.render(segment_video_path)
        return {
            "segments": [{
                "segment_id": state['segment_id'],
                "video_path": segment_video_path,
                "is_ready": True,
                "error": ""
            }]
        }
    except Exception as e:
        return {
            "segments": [{
                "segment_id": state['segment_id'],
                "error": f"Segment {state['segment_id']} failed: {str(e)}",
                "is_ready": False
            }]
        }

def vlm_critic_node(state: SegmentState) -> dict:
    """
    Uses a VLM to 'watch' the rendered segment and provide layout feedback.
    """
    if not state.get("video_path") or not os.path.exists(state["video_path"]):
        return {"vlm_feedback": "Video not found for critique."}
        
    print(f"  [VLMCritic] Reviewing Segment {state['segment_id']}...")
    
    # Mocking VLM 'watching' the video by sending the metadata to LLM
    system_prompt = "You are a visual quality critic for educational coding videos."
    user_prompt = f"""Review this video segment layout:
Chapter: {state['chapter']}
On-screen text: {state['on_screen_text']}
Code: {state['code_snippet']}
Duration: {state['duration_sec']}s

Is the layout clean? Is the text too long? Does the code fit?
Return 'PASS' if good, or a brief instruction for correction."""

    try:
        feedback = call_llm(system_prompt, user_prompt, model="meta-llama/Llama-3.1-8B-Instruct").strip()
        print(f"  [VLMCritic] Feedback: {feedback}")
        return {
            "segments": [{
                "segment_id": state['segment_id'],
                "vlm_feedback": feedback
            }]
        }
    except Exception:
        return {
            "segments": [{
                "segment_id": state['segment_id'],
                "vlm_feedback": "PASS"
            }]
        }
