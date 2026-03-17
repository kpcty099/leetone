"""
Base Visualizer — Phase 2
Abstract wrapper around Manim to generate algorithm animation MP4 clips.
All problem-specific visualizers inherit from this class.
"""

import os
import subprocess
import tempfile
import sys


class BaseVisualizer:
    """
    Renders a Manim animation and returns the path to the MP4 output file.
    
    Usage:
        viz = ArrayVisualizer(problem_data, test_case)
        clip_path = viz.render(output_dir)
    """

    MANIM_QUALITY = "-ql"  # Low quality for speed; use -qh for production

    def __init__(self, problem_data: dict, test_case: dict):
        self.problem_data = problem_data
        self.test_case = test_case
        self.slug = problem_data.get("slug", "unknown")

    def get_manim_scene_code(self) -> str:
        """
        Override in subclasses to return the full Manim Python scene script as a string.
        Must define a class named `AlgorithmScene(Scene)`.
        """
        raise NotImplementedError("Subclasses must implement get_manim_scene_code()")

    def render(self, output_dir: str) -> str:
        """
        Writes the Manim scene code to a temp file, runs Manim, and returns the MP4 path.
        Returns None if rendering fails.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Write scene code to temp file
        scene_code = self.get_manim_scene_code()
        tmp_script = os.path.join(output_dir, f"{self.slug}_scene.py")
        with open(tmp_script, "w", encoding="utf-8") as f:
            f.write(scene_code)

        # Run Manim
        cmd = [
            sys.executable, "-m", "manim",
            self.MANIM_QUALITY,
            tmp_script,
            "AlgorithmScene",
            "--output_file", f"{self.slug}_animation",
            "--media_dir", output_dir,
        ]

        try:
            print(f"  [Manim] Rendering {self.slug}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"  [Manim] Error: {result.stderr[-500:]}")
                return None

            # Find the output MP4
            for root, dirs, files in os.walk(output_dir):
                for fname in files:
                    if fname.endswith(".mp4") and self.slug in fname:
                        return os.path.join(root, fname)

            print(f"  [Manim] Output MP4 not found after rendering.")
            return None

        except subprocess.TimeoutExpired:
            print(f"  [Manim] Timeout rendering {self.slug}")
            return None
        except Exception as e:
            print(f"  [Manim] Exception: {e}")
            return None


def get_visualizer_for_problem(problem_data: dict, test_case: dict):
    """
    Automatically selects the correct visualizer based on problem tags.
    """
    tags = [t.lower() for t in problem_data.get("tags", [])]

    if any(t in tags for t in ["linked-list"]):
        from src.visualizers.linkedlist_visualizer import LinkedListVisualizer
        return LinkedListVisualizer(problem_data, test_case)
    elif any(t in tags for t in ["tree", "binary-tree", "binary-search-tree"]):
        from src.visualizers.tree_visualizer import TreeVisualizer
        return TreeVisualizer(problem_data, test_case)
    elif any(t in tags for t in ["dynamic-programming"]):
        from src.visualizers.dp_table_visualizer import DPTableVisualizer
        return DPTableVisualizer(problem_data, test_case)
    elif any(t in tags for t in ["hash-table", "hash-map"]):
        from src.visualizers.hashmap_visualizer import HashmapVisualizer
        return HashmapVisualizer(problem_data, test_case)
    else:
        # Default: array/two-pointer visualizer
        from src.visualizers.array_visualizer import ArrayVisualizer
        return ArrayVisualizer(problem_data, test_case)
