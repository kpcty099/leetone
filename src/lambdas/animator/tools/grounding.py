import os
from typing import List, Dict, Any
from src.core.state import SegmentState

def mock_whisperx_timestamps(text: str, duration_sec: float) -> List[Dict[str, Any]]:
    """
    Mocks WhisperX word-level timestamps.
    Evenly distributes the words across the duration of the audio.
    """
    words = text.split()
    if not words:
        return []
        
    time_per_word = duration_sec / len(words)
    timestamps = []
    
    current_time = 0.0
    for word in words:
        start = current_time
        end = current_time + time_per_word
        timestamps.append({
            "word": word,
            "start": round(start, 2),
            "end": round(end, 2)
        })
        current_time = end
        
    return timestamps

def mock_ui_tars_spatial_mapping(code_snippet: str, style_guide: dict, pad_left: int = 80, pad_top: int = 240) -> List[Dict[str, Any]]:
    """
    Mocks UI-TARS spatial coordinate mapping.
    Calculates the exact (x, y) bounding box for each word in the code block.
    """
    if not code_snippet:
        return []
        
    font_size = style_guide.get("font_size", 34)
    padding = style_guide.get("padding", 20)
    
    # Base layout offsets based on typical CinematicRenderer defaults
    x_offset = pad_left + padding
    y_offset = pad_top + padding
    
    lines = code_snippet.split('\n')
    coordinates = []
    
    for line in lines:
        words = line.split()
        current_x = x_offset
        for word in words:
            # Approximate width based on monospace font
            word_width = len(word) * (font_size * 0.6)  # 0.6 is a typical character aspect ratio
            word_height = font_size + 10
            
            coordinates.append({
                "word": word,
                "bbox": [current_x, y_offset, current_x + word_width, y_offset + word_height]
            })
            
            current_x += word_width + (font_size * 0.6) # Add space width
            
        y_offset += font_size + 10 # Line spacing
        
    return coordinates

def grounding_node(state: SegmentState, audio_duration: float) -> dict:
    """
    Paper2Video: Spatial-Temporal Grounding (Cursor Builder).
    Aligns audio (WhisperX) and visual (UI-TARS) into a single cursor animation map.
    """
    print(f"  [GroundingAgent] Running spatial-temporal mapping for Segment {state.get('segment_id', 'Unknown')}")
    
    voiceover = state.get("voiceover", "")
    code_snippet = state.get("code_snippet", "")
    style_guide = state.get("style_guide", {"font_size": 34, "padding": 20})
    
    # 1. Temporal: Get word timestamps
    temporal_map = mock_whisperx_timestamps(voiceover, audio_duration)
    
    # 2. Spatial: Get layout coordinates for the code
    spatial_map = mock_ui_tars_spatial_mapping(code_snippet, style_guide)
    
    # In a full implementation, we would align the voiceover words ("variable i") 
    # with the code snippet words ("i = 0") using an LLM or fuzzy matching.
    # For now, we store them in the state to be used by the renderer.
    
    return {
        "temporal_map": temporal_map,
        "spatial_map": spatial_map
    }
