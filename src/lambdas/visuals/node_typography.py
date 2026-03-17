"""
Typography Node — adds keyword overlays and flashcard screens to chapters.
Runs after planning, before rendering. Enriches on_screen_text with
highlighted keywords and generates flashcard_concept for applicable chapters.
"""
import re


# Keywords that always get highlighted in the on-screen text
HIGHLIGHT_KEYWORDS = {
    "O(n²)", "O(n)", "O(n log n)", "O(1)", "O(log n)",
    "Two Pointers", "HashMap", "Hash Map", "HashSet",
    "Linked List", "Binary Search", "Dynamic Programming",
    "Sliding Window", "Stack", "Queue", "Heap", "Graph",
    "BFS", "DFS", "Backtracking", "Greedy",
    "sorted", "duplicates", "pointer", "complement",
    "brute force", "optimal", "TLE", "Space", "Time",
}


def _enrich_on_screen(text: str) -> str:
    """Wrap recognized keywords with a marker for the renderer to highlight."""
    for kw in HIGHLIGHT_KEYWORDS:
        # Case-insensitive, not already wrapped
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(f"[[{kw}]]", text)
    return text


def _make_flashcard(chapter: dict) -> str:
    """Generate a one-line flashcard concept if not already set."""
    existing = chapter.get("flashcard_concept", "").strip()
    if existing:
        return existing

    ch = chapter.get("chapter", "").lower()
    steps = chapter.get("highlight_steps", [])

    if "complexity" in ch or "flashcard" in ch:
        times = [s for s in steps if "O(" in s]
        return " | ".join(times) if times else ""
    elif "data structure" in ch:
        tags = chapter.get("tags", [])
        return f"Use {', '.join(tags[:2])} for O(1) operations" if tags else ""
    elif "optimal" in ch:
        return "Key insight: reduce inner loop with a data structure lookup"
    return ""


def typography_node(state: dict) -> dict:
    """
    LangGraph node: enrich all chapters with keyword highlights and flashcards.
    Purely deterministic — no LLM, no I/O.
    """
    chapters = state.get("chapters", [])
    if not chapters:
        return state

    enriched = []
    for ch in chapters:
        updated = dict(ch)
        # Enrich on_screen_text with keyword markers
        updated["on_screen_text"] = _enrich_on_screen(ch.get("on_screen_text", ""))
        # Generate flashcard concept if missing
        updated["flashcard_concept"] = _make_flashcard(ch)
        enriched.append(updated)

    print(f"[typography_node] ✓ Enriched {len(enriched)} chapters with keyword highlights")
    return {"chapters": enriched}
