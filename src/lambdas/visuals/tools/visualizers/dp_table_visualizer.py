"""
DP Table Visualizer — Phase 2
Generates Manim animation showing a DP table filling up cell by cell.
Used for: Longest Common Subsequence, Knapsack, Edit Distance, etc.
"""

from src.visualizers.base_visualizer import BaseVisualizer


DP_SCENE_TEMPLATE = '''
from manim import *

class AlgorithmScene(Scene):
    def construct(self):
        ROWS   = {rows}
        COLS   = {cols}
        DP     = {dp}    # 2D list of final values
        STEPS  = {steps} # List of (r, c, val, note)
        H_LABELS = {h_labels}
        V_LABELS = {v_labels}
        TITLE  = "{title}"

        title = Text(TITLE, font_size=32, color=BLUE).to_edge(UP, buff=0.2)
        self.play(Write(title))

        cell_size = min(0.7, 5.0 / max(ROWS, COLS))
        table_w = COLS * cell_size
        table_h = ROWS * cell_size

        # Build empty grid
        cells = {{}}
        cell_labels = {{}}

        for r in range(ROWS):
            for c in range(COLS):
                rect = Square(side_length=cell_size, color=GRAY, fill_opacity=0.05)
                rect.move_to(
                    RIGHT * (c * cell_size - table_w/2 + cell_size/2) +
                    DOWN  * (r * cell_size - table_h/2 + cell_size/2)
                )
                cells[(r, c)] = rect
                val_text = Text("", font_size=int(cell_size * 28))
                val_text.move_to(rect.get_center())
                cell_labels[(r, c)] = val_text

        self.play(*[Create(cell) for cell in cells.values()], run_time=0.5)

        # Row/col headers
        for i, lbl in enumerate(H_LABELS[:COLS]):
            t = Text(str(lbl), font_size=int(cell_size * 22), color=YELLOW)
            t.move_to(RIGHT * (i * cell_size - table_w/2 + cell_size/2) + UP * (table_h/2 + 0.3))
            self.add(t)
        for i, lbl in enumerate(V_LABELS[:ROWS]):
            t = Text(str(lbl), font_size=int(cell_size * 22), color=YELLOW)
            t.move_to(LEFT * (table_w/2 + 0.4) + DOWN * (i * cell_size - table_h/2 + cell_size/2))
            self.add(t)

        note_text = Text("", font_size=20, color=ORANGE).to_edge(DOWN, buff=0.4)
        self.add(note_text)

        # Animate cell-by-cell filling
        for step in STEPS:
            r, c, val, note = step
            rect = cells[(r, c)]
            old_label = cell_labels[(r, c)]
            new_label = Text(str(val), font_size=int(cell_size * 26), color=WHITE)
            new_label.move_to(rect.get_center())

            new_note = Text(note, font_size=18, color=ORANGE).to_edge(DOWN, buff=0.4)

            self.play(
                rect.animate.set_fill(BLUE, opacity=0.4),
                Transform(old_label, new_label),
                Transform(note_text, new_note),
                run_time=0.4
            )
            self.play(
                rect.animate.set_fill(GREEN, opacity=0.2),
                run_time=0.2
            )

        self.wait(1.5)
'''


class DPTableVisualizer(BaseVisualizer):
    """Visualizer for DP problems that fill a 2D table."""

    def get_manim_scene_code(self) -> str:
        tc = self.test_case or {}
        # Generic example: LCS / Edit Distance style
        s1 = tc.get("s1", tc.get("text1", "ABCDE"))
        s2 = tc.get("s2", tc.get("text2", "ACE"))

        if isinstance(s1, list):
            s1 = "".join(map(str, s1))
        if isinstance(s2, list):
            s2 = "".join(map(str, s2))

        rows = len(s2) + 1
        cols = len(s1) + 1
        h_labels = [""] + list(s1[:cols - 1])
        v_labels = [""] + list(s2[:rows - 1])

        # Build LCS DP table as example
        dp = [[0] * cols for _ in range(rows)]
        steps = []
        for r in range(1, rows):
            for c in range(1, cols):
                if s2[r - 1] == s1[c - 1]:
                    dp[r][c] = dp[r - 1][c - 1] + 1
                    note = f"Match: s2[{r-1}]={s2[r-1]} == s1[{c-1}]={s1[c-1]} -> dp[{r}][{c}]={dp[r][c]}"
                else:
                    dp[r][c] = max(dp[r - 1][c], dp[r][c - 1])
                    note = f"No match → max({dp[r-1][c]}, {dp[r][c-1]}) = {dp[r][c]}"
                steps.append((r, c, dp[r][c], note))

        # Cap to avoid huge animations
        steps = steps[:30]
        rows = min(rows, 7)
        cols = min(cols, 10)

        title = self.problem_data.get("title", "DP Problem")
        return DP_SCENE_TEMPLATE.format(
            rows=rows, cols=cols,
            dp=repr(dp[:rows]),
            steps=repr(steps[:30]),
            h_labels=repr(h_labels[:cols]),
            v_labels=repr(v_labels[:rows]),
            title=title,
        )
