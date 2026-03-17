"""
Recovery Stitcher — Quick assembly of rendered chapters using 'chain' method.
"""
import os
import sys
import moviepy.editor as mp

# Ensure project root is in path
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"DEBUG: Project Root = {root}")
sys.path.insert(0, root)
print(f"DEBUG: sys.path[0] = {sys.path[0]}")

from src.lambdas.post_process.node_thumbnail import generate_intro_clip
from src.lambdas.post_process.node_stitcher import _make_card_clip

def recover():
    slug = "valid-parentheses"
    title = "Valid Parentheses"
    difficulty = "Easy"
    
    video_dir = "video_temp/video"
    output_dir = "output"
    final_path = os.path.join(output_dir, f"{slug}_final.mp4")
    
    # 1. Load chapters
    chapters = []
    for i in range(1, 9):
        ch_path = os.path.join(video_dir, f"ch{i:02d}.mp4")
        if os.path.exists(ch_path):
            chapters.append({
                "segment_id": i,
                "video_path": ch_path,
                "chapter": f"Chapter {i}",
                "tags": ["Stack", "String"]
            })
    
    print(f"Found {len(chapters)} rendered chapters.")
    
    # 2. Build clips
    clips = []
    try:
        intro = generate_intro_clip(title, slug, difficulty, ["Stack", "String"])
        clips.append(intro)
        print("Prepended intro clip.")
    except Exception as e:
        print(f"Intro failed: {e}")

    for ch in chapters:
        card = _make_card_clip(ch)
        clips.append(card)
        
        vid = mp.VideoFileClip(ch["video_path"]).crossfadein(0.5)
        clips.append(vid)
        
    # 3. Fast stitch
    print("Stitching with method='chain' (this should be fast)...")
    final = mp.concatenate_videoclips(clips, method="chain")
    
    final.write_videofile(
        final_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        verbose=True,
        logger='bar'
    )
    print(f"✓ Video saved to {final_path}")

if __name__ == "__main__":
    recover()
