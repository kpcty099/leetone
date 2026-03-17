"""
Linked List Visualizer — Phase 2
Generates Manim animation for linked list operations:
- Add Two Numbers
- Reverse Linked List
- Merge Sorted Lists
- Detect Cycle
"""

from src.visualizers.base_visualizer import BaseVisualizer


LINKEDLIST_SCENE_TEMPLATE = '''
from manim import *

class AlgorithmScene(Scene):
    def construct(self):
        NODES   = {nodes}
        STEPS   = {steps}
        TITLE   = "{title}"
        APPROACH = "{approach}"

        title = Text(TITLE, font_size=34, color=BLUE).to_edge(UP, buff=0.3)
        approach_label = Text(APPROACH, font_size=20, color=YELLOW).next_to(title, DOWN, buff=0.1)
        self.play(Write(title), FadeIn(approach_label))
        self.wait(0.4)

        # ── Draw linked list nodes ──────────────────────────────
        n = len(NODES)
        node_groups = []
        rects = []
        val_texts = []
        arrows = []

        for i, val in enumerate(NODES):
            rect = RoundedRectangle(width=0.9, height=0.7, corner_radius=0.1,
                                   color=BLUE, fill_opacity=0.15)
            rect.shift(RIGHT * (i * 1.5) - RIGHT * (n * 1.5 / 2))
            val_text = Text(str(val), font_size=26).move_to(rect.get_center())
            rects.append(rect)
            val_texts.append(val_text)

            if i < n - 1:
                arr = Arrow(
                    start=rect.get_right(),
                    end=rect.get_right() + RIGHT * 0.6,
                    color=WHITE, buff=0.05, stroke_width=2
                )
                arrows.append(arr)

        node_vgroup = VGroup(*rects, *val_texts)
        self.play(Create(VGroup(*rects)), Write(VGroup(*val_texts)))
        for arr in arrows:
            self.play(Create(arr), run_time=0.2)
        self.wait(0.3)

        # Pointer label
        ptr_text = Text("curr", font_size=18, color=GREEN)
        ptr_arrow = Arrow(start=DOWN * 0.4, end=ORIGIN, color=GREEN, buff=0)
        note_text = Text("", font_size=22, color=ORANGE).to_edge(DOWN, buff=0.5)

        # ── Animate steps ──────────────────────────────────────
        carry_text = None
        for step in STEPS:
            animations = []

            # Highlight current node
            if "current" in step:
                ci = step["current"]
                ptr_arrow.move_to(rects[ci].get_bottom() + DOWN * 0.4)
                ptr_text.next_to(ptr_arrow, DOWN, buff=0.05)
                animations += [FadeIn(ptr_arrow), FadeIn(ptr_text)]
                animations.append(rects[ci].animate.set_fill(GREEN, opacity=0.3))

            # Show carry
            if "carry" in step:
                carry_val = step["carry"]
                new_carry = Text(f"carry = {{carry_val}}", font_size=22, color=PURPLE)
                new_carry.to_edge(LEFT).shift(DOWN * 2)
                if carry_text:
                    animations.append(Transform(carry_text, new_carry))
                else:
                    carry_text = new_carry
                    animations.append(FadeIn(carry_text))

            # Step note
            if "note" in step:
                new_note = Text(step["note"], font_size=20, color=ORANGE).to_edge(DOWN, buff=0.5)
                animations.append(Transform(note_text, new_note))

            if animations:
                self.play(*animations, run_time=0.7)
            self.wait(0.6)

            # Reset highlight
            if "current" in step:
                ci = step["current"]
                self.play(rects[ci].animate.set_fill(BLUE, opacity=0.15), run_time=0.2)

        self.wait(1)
        done = Text("✓ Complete!", font_size=28, color=GREEN).to_edge(DOWN, buff=0.5)
        self.play(Transform(note_text, done))
        self.wait(1.5)
'''


class LinkedListVisualizer(BaseVisualizer):
    """Visualizer for linked list problems."""

    def get_manim_scene_code(self) -> str:
        tc = self.test_case or {}
        # Accept l1 as a list or a comma-separated string
        l1 = tc.get("l1", tc.get("head", tc.get("input", [2, 4, 3])))
        if isinstance(l1, str):
            try:
                l1 = list(map(int, l1.strip("[]").split(",")))
            except Exception:
                l1 = [2, 4, 3]

        nodes = l1[:10]  # Cap at 10 for visibility
        n = len(nodes)
        steps = []
        carry = 0
        for i in range(n):
            val = nodes[i]
            total = val + carry
            digit = total % 10
            carry = total // 10
            steps.append({
                "current": i,
                "carry": carry,
                "note": f"digit={val}, result={digit}, carry={carry}"
            })

        title = self.problem_data.get("title", "Linked List Problem")
        approach = "Node-by-Node Traversal"

        return LINKEDLIST_SCENE_TEMPLATE.format(
            nodes=repr(nodes),
            steps=repr(steps),
            title=title,
            approach=approach,
        )
