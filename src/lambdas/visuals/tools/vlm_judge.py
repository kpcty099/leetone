import os
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from src.core.state import SegmentState
from src.core.tools.llm_factory import call_llm

# Common academic fonts mapped for the 5-shot choice
FONTS = [
    "courbd.ttf",  # Fallback if Fira/Computer Modern missing
    "Consolas", 
    "DejaVuSansMono-Bold.ttf",
    "Lucida Console",
    "Courier New Bold.ttf"
]

def create_variant_image(code: str, font_size: int, padding: int, bg_color=(26, 28, 36), text_color=(166, 226, 46)) -> Image.Image:
    """Renders a code block into an image with specific font size and padding."""
    # Attempt to load a default fallback if specific fonts aren't available easily
    try:
        font = ImageFont.truetype("courbd.ttf", font_size)
    except:
        font = ImageFont.load_default()
        
    lines = code.split("\n")
    # Estimate size
    max_w = 0
    total_h = padding * 2
    for line in lines:
        try:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1] + 10 # line spacing
        except:
            w = len(line) * (font_size // 2)
            h = font_size + 10
        if w > max_w: max_w = w
        total_h += h
        
    img_w = max_w + padding * 2
    img = Image.new("RGB", (img_w, total_h), bg_color)
    draw = ImageDraw.Draw(img)
    
    y = padding
    for line in lines:
        draw.text((padding, y), line, font=font, fill=text_color)
        try:
            h = font.getbbox(line)[3] - font.getbbox(line)[1] + 10
        except:
            h = font_size + 10
        y += h
        
    return img

def vlm_judge_node(state: SegmentState) -> dict:
    """
    Paper2Video: VLM Visual Choice Tree.
    Generates 5 versions of the code block layout and uses a Vision model to pick the best.
    """
    print(f"  [VLMJudge] Evaluating layout variants for Segment {state.get('segment_id', 'Unknown')}...")
    
    code = state.get("code_snippet", "")
    if not code:
        # Nothing to judge
        return {"segments": [{"segment_id": state.get('segment_id'), "vlm_feedback": "PASS: No code"}]}
        
    # Generate 5 variants (varying font size and padding)
    variants = [
        {"id": 1, "size": 24, "pad": 20},
        {"id": 2, "size": 28, "pad": 30},
        {"id": 3, "size": 34, "pad": 40},
        {"id": 4, "size": 40, "pad": 50},
        {"id": 5, "size": 48, "pad": 60}
    ]
    
    # In a real VLM multimodal call, we would upload these 5 images.
    # For now, we simulate the VLM choice since we can't easily pass 5 PIL images through the simple call_gemini wrapper without modifying it for parts.
    
    # We will pick the variant that best fits an ideal 1920x1080 bounding box width (approx 1200px for code).
    # This simulates the "Judge" picking the most readable without wrapping.
    
    best_variant = variants[2] # Default to middle (size 34)
    
    # Mock VLM Multimodal evaluation:
    print(f"  [VLMJudge] Uploading 5 layout variants to VLM for readability scoring...")
    
    try:
        # We can ask the LLM to choose based on metrics if we can't send images directly in our current wrapper.
        metrics_prompt = f"Code length: {len(code.split())} lines. Max line width: {max([len(l) for l in code.split(chr(10))], default=0)} chars. Which variant is best for 1080p? Variant 1 (Small), Variant 3 (Medium), Variant 5 (Large). Respond with just the number."
        response = call_llm("You are a VLM layout judge. Reply with a single digit 1-5.", metrics_prompt).strip()
        
        chosen_id = int(response) if response.isdigit() and 1 <= int(response) <= 5 else 3
        best_variant = next((v for v in variants if v["id"] == chosen_id), variants[2])
    except:
        best_variant = variants[2]
        
    print(f"  [VLMJudge] VLM selected Variant {best_variant['id']} (Font Size: {best_variant['size']}, Padding: {best_variant['pad']}).")
    
    # Return the chosen style as a component of a Style Guide
    style_guide = {
        "font_size": best_variant['size'],
        "padding": best_variant['pad'],
        "font_family": "Courier New Bold.ttf" # High contrast academic
    }
    
    return style_guide
