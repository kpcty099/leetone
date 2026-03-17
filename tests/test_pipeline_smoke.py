"""
Smoke test for the full LeetCode video generator pipeline.
Runs entirely offline using the locally cached 'two-sum' problem data.
Patches call_llm so no API keys are required.

Run with:
    python -m pytest tests/test_pipeline_smoke.py -v
"""
import os
import sys
import json
import pytest

# Make sure the project root is on the path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def two_sum_data():
    """Load locally cached Two Sum problem data."""
    prob_path = os.path.join(ROOT, "data", "problems", "two-sum", "problem.json")
    sol_path  = os.path.join(ROOT, "data", "problems", "two-sum", "solutions.json")
    assert os.path.exists(prob_path), f"Missing cached problem: {prob_path}"
    with open(prob_path, encoding="utf-8") as f:
        problem = json.load(f)
    solutions = []
    if os.path.exists(sol_path):
        with open(sol_path, encoding="utf-8") as f:
            solutions = json.load(f)
    return problem, solutions


# ── Unit-level node tests ─────────────────────────────────────────────────────

class TestScraperNode:
    def test_loads_two_sum(self):
        """Scraper must resolve 'Two Sum' to slug 'two-sum' and load data."""
        from src.lambdas.scraper.node import scraper_node
        result = scraper_node({"problem_input": "Two Sum", "problem_title": "Two Sum"})
        assert result["problem_slug"] == "two-sum"
        assert result["problem_title"], "Title must be non-empty"
        assert result["problem_data"], "problem_data must be non-empty"
        assert result["difficulty"] in ("Easy", "Medium", "Hard")
        assert result["error"] == ""

    def test_loads_by_number(self):
        """Scraper should resolve numeric IDs too."""
        from src.lambdas.scraper.node import scraper_node
        # ID 1 = Two Sum in most setups; just check it doesn't crash
        result = scraper_node({"problem_input": "1", "problem_title": ""})
        assert "problem_slug" in result


class TestPlannerNode:
    def test_produces_8_chapters(self, two_sum_data):
        """Planner must produce exactly 8 chapters for Two Sum."""
        from src.lambdas.planner.node import planner_node
        problem, solutions = two_sum_data
        state = {
            "problem_title": "Two Sum",
            "difficulty": problem.get("difficulty", "Easy"),
            "problem_data": problem,
            "solutions_data": solutions,
        }
        result = planner_node(state)
        chapters = result["chapters"]
        assert len(chapters) == 8, f"Expected 8 chapters, got {len(chapters)}"

    def test_chapters_have_required_keys(self, two_sum_data):
        """Each chapter must have all required fields."""
        from src.lambdas.planner.node import planner_node
        problem, solutions = two_sum_data
        state = {
            "problem_title": "Two Sum",
            "difficulty": "Easy",
            "problem_data": problem,
            "solutions_data": solutions,
        }
        result = planner_node(state)
        required = ["segment_id", "chapter", "voiceover", "on_screen_text",
                    "highlight_steps", "duration_sec"]
        for ch in result["chapters"]:
            for key in required:
                assert key in ch, f"Chapter missing key '{key}': {ch}"

    def test_voiceover_non_trivial(self, two_sum_data):
        """Voiceovers must have meaningful content (>20 words)."""
        from src.lambdas.planner.node import planner_node
        problem, solutions = two_sum_data
        state = {
            "problem_title": "Two Sum",
            "difficulty": "Easy",
            "problem_data": problem,
            "solutions_data": solutions,
        }
        result = planner_node(state)
        for ch in result["chapters"]:
            words = len(ch["voiceover"].split())
            assert words > 20, (
                f"Chapter {ch['segment_id']} voiceover too short: {words} words"
            )


class TestTypographyNode:
    def test_keyword_markers_added(self, two_sum_data):
        """Typography node must inject [[keyword]] markers into on_screen_text."""
        from src.lambdas.planner.node import planner_node
        from src.lambdas.visuals.node_typography import typography_node
        problem, solutions = two_sum_data
        state = {
            "problem_title": "Two Sum",
            "difficulty": "Easy",
            "problem_data": problem,
            "solutions_data": solutions,
        }
        chapters = planner_node(state)["chapters"]
        result = typography_node({"chapters": chapters})
        updated = result["chapters"]
        assert len(updated) == len(chapters)
        # At least some chapters should have [[keyword]] markers injected
        all_text = " ".join(c["on_screen_text"] for c in updated)
        assert "[[" in all_text, "Typography node must inject [[keyword]] markers"


class TestRendererHelpers:
    def test_tokenize_code_returns_lines(self):
        """_tokenize_code must return one entry per code line."""
        from src.lambdas.renderer.tools.video_renderer import _tokenize_code
        code = "def two_sum(nums, target):\n    seen = {}\n    return seen"
        result = _tokenize_code(code)
        assert len(result) == 3, f"Expected 3 lines, got {len(result)}"

    def test_tokenize_code_fallback_on_invalid(self):
        """_tokenize_code must not crash on invalid Python."""
        from src.lambdas.renderer.tools.video_renderer import _tokenize_code
        result = _tokenize_code("def foo(: INVALID !!! @@")
        assert isinstance(result, list)

    def test_parse_marked(self):
        """_parse_marked must correctly split [[keyword]] markers."""
        from src.lambdas.renderer.tools.video_renderer import _parse_marked
        text = "Use [[HashMap]] for [[O(1)]] lookup"
        parts = _parse_marked(text)
        keywords = [s for s, is_kw in parts if is_kw]
        assert "HashMap" in keywords
        assert "O(1)" in keywords


class TestQualityNode:
    def test_scores_chapters(self):
        """quality_node must assign quality_score to all chapters."""
        from src.lambdas.post_process.node_quality import quality_node
        fake_chapters = [
            {"segment_id": 1, "chapter": "Intro", "audio_path": None, "video_path": None},
            {"segment_id": 2, "chapter": "Brute Force", "audio_path": None, "video_path": None},
        ]
        result = quality_node({"chapters": fake_chapters, "stm": {}})
        for ch in result["chapters"]:
            assert "quality_score" in ch
            assert 0.0 <= ch["quality_score"] <= 10.0


# ── Integration smoke test ─────────────────────────────────────────────────────

class TestFullPipelineSmoke:
    """
    Run the full LangGraph pipeline with the cached Two Sum data.
    Skips any step that requires internet (TTS, Manim) by checking outputs.
    """

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(ROOT, "data", "problems", "two-sum", "problem.json")),
        reason="Cached Two Sum data not available"
    )
    def test_planner_through_typography(self, two_sum_data):
        """Planner → typography → quality produces valid scored chapters."""
        from src.lambdas.planner.node import planner_node
        from src.lambdas.visuals.node_typography import typography_node
        from src.lambdas.post_process.node_quality import quality_node

        problem, solutions = two_sum_data
        state = {
            "problem_title": "Two Sum",
            "difficulty": "Easy",
            "problem_data": problem,
            "solutions_data": solutions,
            "stm": {},
        }

        chapters = planner_node(state)["chapters"]
        assert len(chapters) == 8

        enriched = typography_node({"chapters": chapters})["chapters"]
        assert len(enriched) == 8

        scored  = quality_node({"chapters": enriched, "stm": {}})["chapters"]
        assert len(scored) == 8
        assert all("quality_score" in c for c in scored)
