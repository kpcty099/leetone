from typing import Annotated, TypedDict, Dict, Any, List, Optional
import operator


class ChapterData(TypedDict):
    """Data for a single video chapter."""
    segment_id: int
    chapter: str           # Human-readable chapter name
    duration_sec: int      # Target duration in seconds
    voiceover: str         # Spoken text for TTS
    on_screen_text: str    # Text shown on screen
    code_snippet: str      # Code to display (syntax-highlighted)
    highlight_steps: List[str]  # Bullet points to show step by step
    flashcard_concept: str # Key concept flashcard text
    tags: List[str]        # Problem tags for visualizer selection

    # Populated by later nodes
    audio_path: Optional[str]      # Path to .mp3 TTS file
    animation_path: Optional[str]  # Path to Manim .mp4 animation
    video_path: Optional[str]      # Path to rendered chapter .mp4


def merge_chapters(left: List[Dict], right: List[Dict]) -> List[Dict]:
    """Reducer that merges chapter updates by segment_id."""
    if not left:
        return right
    if not right:
        return left
    combined = {s['segment_id']: s for s in left}
    for s in right:
        sid = s['segment_id']
        if sid in combined:
            combined[sid].update(s)
        else:
            combined[sid] = s
    return sorted(combined.values(), key=lambda x: x['segment_id'])


class AgentState(TypedDict):
    """Shared state across all LangGraph nodes."""
    # ── Inputs ────────────────────────────────────────────────────────────────
    problem_input: str          # Problem name OR number e.g. "Two Sum" or "1"
    problem_title: str          # Resolved title e.g. "Two Sum"
    problem_slug: str           # URL slug e.g. "two-sum"
    difficulty: str             # Easy / Medium / Hard
    regenerate: bool            # Bypass cache and generate anew
    cache_dir: str              # Path to active version cache (e.g. data/problems/two-sum/v1/)

    # ── Scraped Data ──────────────────────────────────────────────────────────
    problem_data: Dict[str, Any]          # Full problem.json contents
    solutions_data: List[Dict[str, Any]]  # All solutions from solutions.json

    # ── Reasoning & Knowledge (Phase 5) ───────────────────────────────────────
    pattern: str               # e.g., "Two Pointers", "Sliding Window"
    visual_strategy: str        # e.g., "Pointer Motion", "Hashmap Grid"
    reasoning: str             # Detailed LLM logic for the approach
    algorithm_data: Dict[str, Any] # Verified code, test cases, dry run trace

    # ── Plan ──────────────────────────────────────────────────────────────────
    chapters: Annotated[List[ChapterData], merge_chapters]

    # ── Error handling ────────────────────────────────────────────────────────
    error: str                 # Latest error (cleared between retries)
    errors: List[str]          # Accumulated list of ALL errors across all nodes
    retry_count: int           # How many retries have been attempted so far
    stm: Dict[str, Any]        # Short-term memory (run-scoped)

    # ── Final Output ──────────────────────────────────────────────────────────
    final_video_path: str
    thumbnail_path:   str     # YouTube thumbnail (1280×720 PNG)
