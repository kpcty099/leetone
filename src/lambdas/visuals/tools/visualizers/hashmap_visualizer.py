"""
Hashmap Visualizer — Phase 2
Generates Manim animation showing hashmap insert and lookup operations.
Used for: Two Sum, Group Anagrams, Top K Frequent Elements, etc.
"""

from src.visualizers.base_visualizer import BaseVisualizer


HASHMAP_SCENE_TEMPLATE = '''
from manim import *

class AlgorithmScene(Scene):
    def construct(self):
        OPERATIONS = {operations}   # list of ("insert"|"lookup", key, value, note)
        TITLE      = "{title}"
        APPROACH   = "{approach}"

        title = Text(TITLE, font_size=32, color=BLUE).to_edge(UP, buff=0.3)
        approach = Text(APPROACH, font_size=20, color=YELLOW).next_to(title, DOWN, buff=0.1)
        self.play(Write(title), FadeIn(approach))

        # ── Draw HashMap visual (bucket array) ───────────────────
        BUCKETS = 7
        bucket_labels = []
        bucket_rects  = []
        bucket_contents = {{}}

        for i in range(BUCKETS):
            rect = Rectangle(width=1.4, height=0.55, color=GRAY, fill_opacity=0.1)
            rect.move_to(LEFT * 2 + DOWN * (i * 0.6 - BUCKETS * 0.3))
            idx_lbl = Text(str(i), font_size=16, color=GRAY_C).next_to(rect, LEFT, buff=0.1)
            bucket_rects.append(rect)
            bucket_labels.append(idx_lbl)

        self.play(*[Create(r) for r in bucket_rects], *[Write(l) for l in bucket_labels], run_time=0.5)

        note_text = Text("", font_size=20, color=ORANGE).to_edge(DOWN, buff=0.4)
        self.add(note_text)
        stored_texts = {{}}

        for op, key, val, note in OPERATIONS:
            bucket_idx = hash(str(key)) % BUCKETS
            rect = bucket_rects[bucket_idx]

            # Highlight the bucket
            content_str = f"{{key}}: {{val}}"
            content_text = Text(content_str, font_size=16, color=GREEN if op == "insert" else YELLOW)
            content_text.move_to(rect.get_center())

            new_note = Text(note, font_size=18, color=ORANGE).to_edge(DOWN, buff=0.4)

            if op == "insert":
                self.play(
                    rect.animate.set_fill(GREEN, opacity=0.3),
                    FadeIn(content_text),
                    Transform(note_text, new_note),
                    run_time=0.6
                )
                stored_texts[key] = content_text
            elif op == "lookup":
                self.play(
                    rect.animate.set_fill(YELLOW, opacity=0.3),
                    Transform(note_text, new_note),
                    run_time=0.6
                )

            self.wait(0.5)
            self.play(rect.animate.set_fill(WHITE, opacity=0.1), run_time=0.2)

        self.wait(1.5)
        done = Text("✓ Complete!", font_size=26, color=GREEN).to_edge(DOWN, buff=0.4)
        self.play(Transform(note_text, done))
        self.wait(1.5)
'''


class HashmapVisualizer(BaseVisualizer):
    """Visualizer for hash-table based problems."""

    def get_manim_scene_code(self) -> str:
        tc = self.test_case or {}
        nums = tc.get("nums", [2, 7, 11, 15])
        target = tc.get("target", 9)

        if isinstance(nums, str):
            try:
                nums = list(map(int, nums.strip("[]").split(",")))
            except Exception:
                nums = [2, 7, 11, 15]

        # Simulate Two Sum with hashmap
        operations = []
        seen = {}
        for i, num in enumerate(nums[:8]):
            complement = target - num
            if complement in seen:
                operations.append(("lookup", complement, seen[complement],
                                   f"Found complement {complement} at index {seen[complement]}! Answer: [{seen[complement]}, {i}]"))
                break
            else:
                operations.append(("insert", num, i,
                                   f"Store num={num} -> index={i} in hashmap"))
                seen[num] = i

        title = self.problem_data.get("title", "Hash Table Problem")
        approach = "HashMap O(n) Approach"

        return HASHMAP_SCENE_TEMPLATE.format(
            operations=repr(operations),
            title=title,
            approach=approach,
        )
