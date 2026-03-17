"""
Quality Assurance Node — computes quality score for each chapter.
Logs results to LTM. Score < 7.0 triggers a failure report but never halts pipeline.
"""
import os
from src.core.memory import log_chapter_quality, log_error, finish_run


def _score_chapter(chapter: dict) -> float:
    """Compute quality score 0-10 for a single chapter."""
    score = 10.0
    seg_id = chapter.get("segment_id", 0)

    # Audio present: -3 if missing
    if not chapter.get("audio_path") or not os.path.exists(chapter.get("audio_path", "")):
        score -= 3.0
        print(f"  [qa] Ch{seg_id}: WARN no audio (-3)")

    # Video present: -4 if missing (critical)
    video = chapter.get("video_path", "")
    if not video or not os.path.exists(video):
        score -= 4.0
        print(f"  [qa] Ch{seg_id}: WARN no video (-4)")
    else:
        # Check file size > 50KB
        size = os.path.getsize(video)
        if size < 50_000:
            score -= 2.0
            print(f"  [qa] Ch{seg_id}: WARN video too small {size}B (-2)")

    # Animation present for visual chapters: -1 if expected but missing
    ch_name = chapter.get("chapter", "").lower()
    needs_animation = any(k in ch_name for k in ["dry run", "brute force", "optimal"])
    if needs_animation and not chapter.get("animation_path"):
        score -= 1.0

    return max(0.0, score)


def quality_node(state: dict) -> dict:
    """
    LangGraph node: score all chapters and log results to LTM.
    Never blocks the pipeline — just reports.
    """
    chapters = state.get("chapters", [])
    run_id   = state.get("stm", {}).get("run_id")

    if not chapters:
        return state

    total_score = 0.0
    scored_chapters = []

    for chapter in chapters:
        score = _score_chapter(chapter)
        total_score += score
        updated = {**chapter, "quality_score": score}
        scored_chapters.append(updated)

        # Log to LTM
        if run_id:
            try:
                log_chapter_quality(run_id, updated)
            except Exception:
                pass

        if score < 7.0:
            print(f"  [qa] Ch{chapter.get('segment_id')}: LOW quality score {score:.1f}/10")

    avg_score = total_score / len(chapters) if chapters else 0.0
    print(f"[quality_node] Average quality score: {avg_score:.1f}/10")

    return {"chapters": scored_chapters, "error": ""}
