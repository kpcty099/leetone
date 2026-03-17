"""
Array Visualizer — Phase 2
Generates Manim animation for array-based algorithms:
- Two Pointer
- Sliding Window
- Binary Search  
- Prefix Sum
"""

from src.visualizers.base_visualizer import BaseVisualizer


ARRAY_SCENE_TEMPLATE = '''
from manim import *

class AlgorithmScene(Scene):
    def construct(self):
        # ── Config ──────────────────────────────────────────────
        ARRAY    = {array}
        STEPS    = {steps}   # list of dicts: {{left, right, highlight, label, note}}
        TITLE    = "{title}"
        APPROACH = "{approach}"

        # ── Title ────────────────────────────────────────────────
        title = Text(TITLE, font_size=36, color=BLUE).to_edge(UP, buff=0.3)
        approach_label = Text(APPROACH, font_size=22, color=YELLOW).next_to(title, DOWN, buff=0.1)
        self.play(Write(title), FadeIn(approach_label))
        self.wait(0.5)

        # ── Draw array ───────────────────────────────────────────
        n = len(ARRAY)
        boxes = VGroup()
        labels = VGroup()
        idx_labels = VGroup()

        for i, val in enumerate(ARRAY):
            box = Square(side_length=0.8, color=WHITE, fill_opacity=0.1)
            box.shift(RIGHT * (i - n/2 + 0.5) * 0.9)
            lbl = Text(str(val), font_size=28).move_to(box.get_center())
            idx = Text(str(i), font_size=18, color=GRAY).next_to(box, DOWN, buff=0.1)
            boxes.add(box)
            labels.add(lbl)
            idx_labels.add(idx)

        array_group = VGroup(boxes, labels, idx_labels).shift(DOWN * 0.5)
        self.play(Create(boxes), Write(labels), Write(idx_labels))
        self.wait(0.3)

        # Left/right pointer arrows
        left_arrow  = Arrow(start=UP*0.5, end=ORIGIN, color=GREEN,  buff=0)
        right_arrow = Arrow(start=UP*0.5, end=ORIGIN, color=RED,    buff=0)
        left_label  = Text("L", font_size=20, color=GREEN)
        right_label = Text("R", font_size=20, color=RED)

        note_text = Text("", font_size=22, color=ORANGE).to_edge(DOWN, buff=0.5)

        # ── Animate steps ─────────────────────────────────────────
        for step in STEPS:
            animations = []

            # Move left pointer
            if "left" in step:
                li = step["left"]
                target = boxes[li].get_top() + UP * 0.6
                left_arrow.move_to(target + DOWN * 0.3)
                left_label.next_to(left_arrow, UP, buff=0.05)
                animations += [FadeIn(left_arrow), FadeIn(left_label)]

            # Move right pointer
            if "right" in step:
                ri = step["right"]
                target = boxes[ri].get_top() + UP * 0.6
                right_arrow.move_to(target + DOWN * 0.3)
                right_label.next_to(right_arrow, UP, buff=0.05)
                animations += [FadeIn(right_arrow), FadeIn(right_label)]

            # Highlight cells
            if "highlight" in step:
                for hi in step["highlight"]:
                    animations.append(boxes[hi].animate.set_fill(YELLOW, opacity=0.4))

            # Step note
            if "note" in step:
                new_note = Text(step["note"], font_size=22, color=ORANGE).to_edge(DOWN, buff=0.5)
                animations.append(Transform(note_text, new_note))

            if animations:
                self.play(*animations, run_time=0.8)
            self.wait(0.6)

            # Reset highlights
            for box in boxes:
                self.play(box.animate.set_fill(WHITE, opacity=0.1), run_time=0.2)

        self.wait(1)
        done = Text("✓ Complete!", font_size=30, color=GREEN).to_edge(DOWN, buff=0.5)
        self.play(Transform(note_text, done))
        self.wait(1.5)
'''


class ArrayVisualizer(BaseVisualizer):
    """Visualizer for array-based problems (two-pointer, sliding window, binary search)."""

    def get_manim_scene_code(self) -> str:
        # Extract test case values
        tc = self.test_case or {}
        nums = tc.get("nums", tc.get("array", tc.get("input", [1, 2, 3, 4, 5])))
        if isinstance(nums, str):
            try:
                nums = list(map(int, nums.strip("[]").split(",")))
            except Exception:
                nums = [1, 2, 3, 4, 5]

        # Build animation steps from test case
        n = len(nums)
        steps = []
        # Two-pointer style: show convergence
        l, r = 0, n - 1
        while l <= r:
            steps.append({
                "left": l,
                "right": r,
                "highlight": [l, r],
                "note": f"Checking nums[{l}]={nums[l]} + nums[{r}]={nums[r]}"
            })
            l += 1
            r -= 1
            if len(steps) >= 8:
                break

        title = self.problem_data.get("title", "Array Problem")
        approach = "Two Pointer Approach"

        return ARRAY_SCENE_TEMPLATE.format(
            array=repr(nums[:12]),  # Cap at 12 elements for visibility
            steps=repr(steps),
            title=title,
            approach=approach,
        )
