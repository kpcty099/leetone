"""
Stitcher Node — concatenates all chapter .mp4 files into final video.
Adds an intro title card, chapter title cards, and smooth fade transitions.
Phase 4: intro clip prepended via thumbnail_generator.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
from .node_thumbnail import generate_intro_clip

OUTPUT_DIR = "output"

BG_DARK      = (14, 14, 18)
ACCENT_CYAN  = (0, 212, 255)
TEXT_WHITE   = (240, 240, 245)
W, H = 1920, 1080
FPS  = 24
CARD_DUR     = 1.5   # seconds for chapter title card


def _get_font(size):
    for path in ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _chapter_card_frame(chapter_num: int, chapter_name: str, color: tuple) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    font_num  = _get_font(80)
    font_name = _get_font(48)

    # Center circle
    cx, cy = W // 2, H // 2
    draw.ellipse([cx-90, cy-90, cx+90, cy+90], outline=color, width=4)
    ch_text = str(chapter_num)
    bb = draw.textbbox((0, 0), ch_text, font=font_num)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    draw.text((cx - tw//2, cy - th//2), ch_text, font=font_num, fill=color)

    # Chapter name below
    name_lines = chapter_name.split("\n")
    ny = cy + 110
    for line in name_lines:
        bb2 = draw.textbbox((0, 0), line, font=font_name)
        tw2 = bb2[2] - bb2[0]
        draw.text(((W - tw2) // 2, ny), line, font=font_name, fill=TEXT_WHITE)
        ny += 60

    # Bottom line
    draw.rectangle([W//4, H-8, 3*W//4, H], fill=color)
    return np.array(img)


def _make_card_clip(chapter: dict) -> mp.VideoClip:
    seg_id  = chapter["segment_id"]
    ch_name = chapter["chapter"]
    colors = [
        ACCENT_CYAN, (255, 140, 0), (78, 230, 100),
        (255, 80, 140), (255, 220, 50), (0, 180, 255),
        (200, 100, 255), (255, 120, 70),
    ]
    color = colors[(seg_id - 1) % len(colors)]
    frame = _chapter_card_frame(seg_id, ch_name, color)

    return mp.ImageClip(frame).set_duration(CARD_DUR).set_fps(FPS).crossfadein(0.3)


def stitcher_node(state: dict) -> dict:
    """
    LangGraph node: stitch all chapter videos into final output.
    """
    chapters   = state.get("chapters", [])
    slug       = state.get("problem_slug", "problem")
    title      = state.get("problem_title", "Problem")
    difficulty = state.get("difficulty", "")

    rendered = [c for c in sorted(chapters, key=lambda x: x["segment_id"])
                if c.get("video_path") and os.path.exists(c["video_path"])]

    if not rendered:
        return {"error": "stitcher_node: no rendered chapters found"}

    cache_dir = state.get("cache_dir", OUTPUT_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    final_path = os.path.join(cache_dir, f"{slug}_final.mp4")

    print(f"[stitcher_node] Stitching {len(rendered)}/{len(chapters)} chapters for '{title}'")

    # ── Cinematic intro clip ──────────────────────────────────────────────
    clips = []
    try:
        tags = rendered[0].get("tags", []) if rendered else []
        intro = generate_intro_clip(title, slug, difficulty, tags)
        clips.append(intro)
        print(f"[stitcher_node] Prepended intro title card ({intro.duration:.1f}s)")
    except Exception as e:
        print(f"[stitcher_node] WARNING: intro clip failed ({e}), skipping")
        clips = []
    for chapter in rendered:
        # Chapter title card
        card = _make_card_clip(chapter)
        clips.append(card)

        # Chapter video with fade in
        ch_clip = mp.VideoFileClip(chapter["video_path"]).crossfadein(0.5)
        clips.append(ch_clip)

    # Final concat with transitions (chain method is faster for matching resolutions)
    final = mp.concatenate_videoclips(clips, method="chain")

    total_min = final.duration / 60
    print(f"[stitcher_node] Final duration: {total_min:.1f} minutes")

    temp_audio = f"{final_path}.temp_audio.m4a"
    final.write_videofile(
        final_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=temp_audio,
        verbose=False,
        logger=None,
    )
    
    # Free Windows File Handles
    final.close()
    for c in clips:
        c.close()

    size_mb = os.path.getsize(final_path) / 1024 / 1024
    print(f"[stitcher_node] [OK] Final video: {size_mb:.0f}MB -> {final_path}")
    return {"final_video_path": final_path, "error": ""}
