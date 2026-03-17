"""
Progress Tracker — Phase 4 addition.
Live Rich-based console dashboard for pipeline runs.
Falls back to plain prints if Rich is not installed.

Usage in nodes:
    from src.core.tools.progress_tracker import tracker
    tracker.node_start("tts")
    tracker.chapter_done(seg_id, "audio")
    tracker.node_done("tts")
"""
import time, sys
from typing import Optional

# ── Rich import (optional) ────────────────────────────────────────────────────
_RICH = True

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    _RICH = False

# Pipeline node order
NODES = [
    "memory_init", "scraper", "test_case_gen", "planner", "discussion_planner",
    "reflection", "reasoning", "semantic_engine", "strategy_selector",
    "motion_choreographer", "typography", "animator", "tts", "multi_tts",
    "renderer", "dialogue_renderer", "quality", "thumbnail", "stitcher",
]

STATUS_ICONS = {
    "pending":  "( )",
    "running":  "[...]",
    "done":     "v",
    "failed":   "(X)",
    "skipped":  "-",
}

LOG_FILE = "data/pipeline_progress.log"

def set_log_path(cache_dir: str):
    global LOG_FILE
    if cache_dir and os.path.exists(cache_dir):
        LOG_FILE = os.path.join(cache_dir, "pipeline_progress.log")

def _internal_log(msg: str):
    import os
    # Ensure dir exists just in case
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


class ProgressTracker:
    """
    Tracks pipeline node and chapter progress.
    Thread-safe for use from parallel renderers.
    """

    def __init__(self):
        self._node_status:    dict[str, str]  = {n: "pending" for n in NODES}
        self._node_times:     dict[str, float] = {}
        self._chapter_flags:  dict[int, dict[str, bool]] = {}  # seg_id → {audio, video, anim}
        self._start_time:     float = time.time()
        self._live:           Optional[object] = None
        self._console = Console() if _RICH else None
        self._total_chapters  = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, total_chapters: int = 0):
        """Call at the beginning of a pipeline run."""
        self._start_time = time.time()
        self._total_chapters = total_chapters
        self._chapter_flags = {i+1: {"audio": False, "video": False, "anim": False}
                                for i in range(total_chapters)}
        if _RICH:
            self._console.rule("[bold cyan]LeetCode Video Generator[/bold cyan]")
            self._console.print(f"  [dim]Chapters: {total_chapters}[/dim]")
        else:
            msg = f"\n{'='*50}\n  Pipeline started - {total_chapters} chapters\n{'='*50}"
            print(msg)
            _internal_log(msg)

    def node_start(self, node: str):
        """Mark a node as running."""
        self._node_status[node] = "running"
        self._node_times[node]  = time.time()
        # Only print if not using a status context
        if not self._live:
            self._print_status(node, "running")

    def node_done(self, node: str, failed: bool = False):
        """Mark a node as completed or failed."""
        status = "failed" if failed else "done"
        self._node_status[node] = status
        elapsed = time.time() - self._node_times.get(node, self._start_time)
        # Always print done/failed to keep it in the history
        self._print_status(node, status, elapsed=elapsed)

    def node_skip(self, node: str):
        """Mark a node as skipped (used for pipeline-2-only nodes in pipeline 1)."""
        self._node_status[node] = "skipped"
        self._print_status(node, "skipped")

    def status_context(self, node: str):
        """Context manager for node status with a spinner."""
        if not _RICH or not self._console:
            return self._fallback_context()
        
        # Display name (capitalized, replaced underscores)
        title = node.replace("_", " ").title()
        return self._console.status(f"[bold yellow]{title}[/bold yellow] in progress...", spinner="dots")

    def _fallback_context(self):
        # Null context fallback for non-rich or console-less environments
        import contextlib
        @contextlib.contextmanager
        def null(): yield
        return null()

    def chapter_done(self, seg_id: int, kind: str):
        """
        Record that a chapter completed a processing step.
        kind: 'audio' | 'video' | 'anim'
        """
        if seg_id not in self._chapter_flags:
            self._chapter_flags[seg_id] = {"audio": False, "video": False, "anim": False}
        self._chapter_flags[seg_id][kind] = True
        done_count = sum(1 for f in self._chapter_flags.values() if f.get(kind))
        total = self._total_chapters or len(self._chapter_flags)
        self._print_chapter(seg_id, kind, done_count, total)

    def summary(self) -> str:
        """Return a one-line summary string."""
        elapsed = time.time() - self._start_time
        done    = sum(1 for s in self._node_status.values() if s == "done")
        failed  = sum(1 for s in self._node_status.values() if s == "failed")
        return (
            f"Nodes: {done} done, {failed} failed | "
            f"Elapsed: {elapsed:.0f}s"
        )

    def print_summary(self):
        """Print final summary."""
        if _RICH:
            self._console.rule("[bold green]Pipeline Complete[/bold green]")
            self._console.print(f"  {self.summary()}")
            self._print_rich_table()
        else:
            print(f"\n{'='*50}\n  {self.summary()}\n{'='*50}")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _print_status(self, node: str, status: str, elapsed: float = 0.0):
        icon = STATUS_ICONS.get(status, "?")
        color_map = {
            "running": "yellow", "done": "green",
            "failed": "red", "skipped": "dim", "pending": "white",
        }
        if _RICH:
            col   = color_map.get(status, "white")
            elaps = f"  [dim]({elapsed:.1f}s)[/dim]" if elapsed else ""
            self._console.print(
                f"  [{col}]{icon}[/{col}]  [bold]{node:<22}[/bold]{elaps}"
            )
        else:
            elaps = f" ({elapsed:.1f}s)" if elapsed else ""
            msg = f"  {icon}  {node:<22}{elaps}"
            print(msg, flush=True)
            _internal_log(msg)

    def _print_chapter(self, seg_id: int, kind: str, done: int, total: int):
        bar_len = 20
        filled  = int(bar_len * done / max(total, 1))
        bar = "#" * filled + "-" * (bar_len - filled)
        msg = f"  [chapter {kind}] Ch{seg_id:02d} done  [{bar}] {done}/{total}"
        if _RICH:
            self._console.print(f"  [dim cyan]{msg}[/dim cyan]")
        else:
            print(msg)

    def _print_rich_table(self):
        if not _RICH:
            return
        table = Table(title="Node Summary", show_header=True, header_style="bold cyan")
        table.add_column("Node", style="bold", width=22)
        table.add_column("Status", width=10)
        for node in NODES:
            status = self._node_status.get(node, "pending")
            icon   = STATUS_ICONS.get(status, "?")
            color  = {"done": "green", "failed": "red", "running": "yellow",
                      "skipped": "dim", "pending": "white"}.get(status, "white")
            table.add_row(node, f"[{color}]{icon} {status}[/{color}]")
        self._console.print(table)


# ── Module-level singleton ─────────────────────────────────────────────────────
tracker = ProgressTracker()
