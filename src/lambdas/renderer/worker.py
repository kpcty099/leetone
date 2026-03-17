import os
import sys
import time
import traceback
import numpy as np
import moviepy.editor as mp
from typing import Dict, Any
from src.core.worker import BaseWorker

# Import the actual rendering logic from video_renderer
# Note: In a full refactor, we would move the rendering functions into a shared module
import src.lambdas.renderer.tools.video_renderer as vr

class RendererWorker(BaseWorker):
    """
    Worker for rendering individual chapters.
    Implementation of the "Local Lambda" for Video Rendering.
    """

    def __init__(self, cache_dir: str):
        super().__init__("renderer", cache_dir)
        # Ensure the video temp dir exists
        os.makedirs(os.path.join(cache_dir, "video"), exist_ok=True)

    def execute(self, payload: Dict[str, Any]) -> Any:
        """
        Payload: {
            "chapter": dict,
            "video_dir": str
        }
        """
        chapter = payload.get("chapter")
        video_dir = payload.get("video_dir", os.path.join(self.cache_dir, "video"))
        
        if not chapter:
            raise ValueError("No chapter data provided to RendererWorker")

        seg_id = chapter["segment_id"]
        ch_name = chapter.get("chapter", "Unknown")
        
        self.log(f"Rendering Chapter {seg_id}: {ch_name}")
        
        # Call the existing core rendering function
        # In a real "Lambda", this would be its own entry point
        result_chapter = vr._make_chapter_video(chapter, video_dir)
        
        if result_chapter.get("video_path") is None:
            raise RuntimeError(f"Rendering failed for chapter {seg_id}")
            
        return result_chapter
