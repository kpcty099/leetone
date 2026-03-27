"""
LangGraph Agent Graph — Full Dual-Pipeline Architecture
========================================================
Routes by difficulty:
  Easy / Medium -> Pipeline 1: Single Tutor
  Hard          -> Pipeline 2: Multi-Tutor Discussion

Pipeline 1 (Single Tutor):
  memory_init -> scraper -> test_case_gen -> planner -> reflection -> typography -> animator -> tts -> renderer -> quality -> stitcher

Pipeline 2 (Multi-Tutor Discussion):
  memory_init -> scraper -> test_case_gen -> discussion_planner -> typography -> animator -> multi_tts -> dialogue_renderer -> quality -> stitcher
"""
from langgraph.graph import StateGraph, END

from src.core.state import AgentState
from src.core.memory import start_run, finish_run, make_stm
from config.providers import LLM_PROVIDER, TTS_PROVIDER
from src.core.tools.progress_tracker import tracker

# ── Modular Lambda Nodes ──────────────────────────────────────────────────────
from src.lambdas.scraper import scraper_node
from src.lambdas.planner import planner_node
from src.lambdas.animator import animator_node
from src.lambdas.tts import tts_node
from src.lambdas.renderer import renderer_node

# ── Feature Nodes ─────────────────────────────────────────────────────────────
from src.lambdas.post_process.node_quality import quality_node
from src.lambdas.post_process.node_stitcher import stitcher_node
from src.lambdas.visuals.node_typography import typography_node
from src.lambdas.post_process.node_thumbnail import thumbnail_node
from src.lambdas.reasoning.node import reasoning_node
from src.lambdas.visuals.node_semantic import semantic_engine_node
from src.lambdas.visuals.node_strategy import strategy_selector_node
from src.lambdas.visuals.node_motion import motion_choreographer_node
from src.lambdas.robustness.node_test_case import test_case_node
from src.lambdas.robustness.node_reflection import reflection_node

# ── Pipeline 2 Nodes ──────────────────────────────────────────────────────────
from src.lambdas.multi_tutor.node_planner import discussion_planner_node
from src.lambdas.multi_tutor.node_tts import multi_tts_node
from src.lambdas.multi_tutor.node_renderer import dialogue_renderer_node


# ── Constants ─────────────────────────────────────────────────────────────────
MAX_RETRIES = 3
HARD_DIFFICULTIES = {"hard"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_hard(state: AgentState) -> bool:
    return state.get("difficulty", "").lower() in HARD_DIFFICULTIES


def _has_error(state: AgentState) -> bool:
    return bool(state.get("error", ""))


def _has_fatal_error(state: AgentState) -> bool:
    return bool(state.get("error", "")) and "fatal" in state.get("error", "").lower()


def _over_limit(state: AgentState) -> bool:
    return state.get("retry_count", 0) >= MAX_RETRIES


def _record_error(state: AgentState, node: str) -> dict:
    err = state.get("error", "")
    existing = list(state.get("errors", []))
    if err:
        msg = f"[{node}] {err}"
        existing.append(msg)
        
        # Log to cache_dir if available
        cache_dir = state.get("cache_dir")
        if cache_dir:
            import os
            os.makedirs(cache_dir, exist_ok=True)
            log_path = os.path.join(cache_dir, "error_log.txt")
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
            except Exception:
                pass
                
    return {"errors": existing, "retry_count": state.get("retry_count", 0) + 1}


# ── Memory Init ───────────────────────────────────────────────────────────────

def _memory_init_wrapper(state: AgentState) -> dict:
    print("[graph] Entering memory_init_wrapper")
    """Initialise STM and log run start to LTM."""
    stm = make_stm()
    slug  = state.get("problem_slug", "unknown")
    title = state.get("problem_title", "Unknown")
    try:
        run_id = start_run(slug, title, LLM_PROVIDER, TTS_PROVIDER)
        stm["run_id"] = run_id
        print(f"[memory] Started run #{run_id} for '{title}'")
    except Exception as e:
        print(f"[memory] LTM init non-fatal: {e}")
    
    tracker.node_start("memory_init")
    tracker.node_done("memory_init")
    return {"stm": stm}


# ── Architecture Selector ─────────────────────────────────────────────────────

def route_after_scraper(state: AgentState) -> str:
    # After scraper, we always go to test_case_gen UNLESS it's a cache hit
    cache_dir = state.get("cache_dir", "")
    if cache_dir:
        import os, glob
        mp4s = glob.glob(os.path.join(cache_dir, "*_final.mp4"))
        if mp4s:
            print(f"[Router] Final video already in cache: {mp4s[0]}")
            return "cache_hit"
    return "test_case_gen"

def route_after_test_case_gen(state: AgentState) -> str:
    if _over_limit(state):
        return "end"
    
    chapters  = state.get("chapters", [])
    
    # Chapters loaded but no final video -> still need to run render + stitch
    if chapters and not all(c.get("video_path") for c in chapters):
        print("[Router] Cached plan loaded. Skipping planner, going to TTS/renderer.")
        if _is_hard(state):
            return "multi_tts"
        return "tts"
    
    # Chapters loaded AND all have video paths -> jump straight to stitcher
    if chapters and all(c.get("video_path") for c in chapters):
        print("[Router] Found cached chapters with videos -> Skipping straight to Stitcher")
        return "stitcher"
    
    # Route to appropriate planner based on difficulty
    if _is_hard(state):
        print(f"[Router] Difficulty=Hard -> Pipeline 2 (Multi-Tutor Discussion)")
        return "discussion_planner"
    print(f"[Router] Difficulty={state.get('difficulty','?')} -> Pipeline 1 (Single Tutor)")
    return "planner"


# ── Pipeline 1 Routers ────────────────────────────────────────────────────────

def route_after_planner(state: AgentState) -> str:
    if _over_limit(state) or not state.get("chapters") or _has_error(state):
        return "end"
    return "reflection"

def route_after_reflection(state: AgentState) -> str:
    if _has_error(state) and not _over_limit(state):
        print("[Router] Reflection flagged issues. Retrying Planner...")
        return "planner"
    return "semantic_engine"

def route_after_semantic_engine(state: AgentState) -> str:
    return "strategy_selector"

def route_after_strategy_selector(state: AgentState) -> str:
    return "motion_choreographer"

def route_after_motion_choreographer(state: AgentState) -> str:
    return "typography"


def route_after_typography(state: AgentState) -> list:
    if _over_limit(state):
        return ["end"]
    # Branch to both animator and tts in parallel
    chapters = state.get("chapters", [])
    is_discussion = any(c.get("is_discussion") for c in chapters)
    
    parallel_nodes = ["animator"]
    if is_discussion:
        parallel_nodes.append("multi_tts")
    else:
        parallel_nodes.append("tts")
        
    return parallel_nodes


def route_after_animator(state: AgentState) -> str:
    if _over_limit(state) or _has_fatal_error(state):
        return "end"
    return "renderer" # In parallel branch, animator now goes to renderer join


def route_after_tts(state: AgentState) -> str:
    if _over_limit(state):
        return "end"
    chapters = state.get("chapters", [])
    if not any(c.get("audio_path") for c in chapters) and _has_fatal_error(state):
        return "end"
    return "renderer"


def route_after_renderer(state: AgentState) -> str:
    if _over_limit(state):
        return "end"
    if not any(c.get("video_path") for c in state.get("chapters", [])):
        return "end"
    return "quality"


# ── Pipeline 2 Routers ────────────────────────────────────────────────────────

def route_after_discussion_planner(state: AgentState) -> str:
    if _over_limit(state) or not state.get("chapters") or _has_error(state):
        return "end"
    return "semantic_engine"


def route_after_multi_tts(state: AgentState) -> str:
    if _over_limit(state):
        return "end"
    if not any(c.get("audio_path") for c in state.get("chapters", [])):
        return "end"
    return "renderer" # Previously went to dialogue_renderer, now part of parallel branch


def route_after_dialogue_renderer(state: AgentState) -> str:
    if _over_limit(state):
        return "end"
    if not any(c.get("video_path") for c in state.get("chapters", [])):
        return "end"
    return "quality"


# ── Shared Routers ────────────────────────────────────────────────────────────

def route_after_quality(state: AgentState) -> str:
    return "thumbnail"   # Quality feeds into thumbnail then stitcher


def route_after_thumbnail(state: AgentState) -> str:
    return "stitcher"    # Always proceed to stitcher


def route_after_stitcher(state: AgentState) -> str:
    chapters = state.get("chapters", [])
    run_id  = state.get("stm", {}).get("run_id")
    final   = state.get("final_video_path", "")
    if final and not _has_error(state):
        dur   = sum(c.get("duration_sec", 0) for c in chapters) / 60
        score = sum(c.get("quality_score", 8.0) for c in chapters) / max(len(chapters), 1)
        if run_id:
            try: finish_run(run_id, "success", score, final, dur)
            except Exception: pass
        return "end_success"
    if run_id:
        try: finish_run(run_id, "failed", 0.0, "", 0.0)
        except Exception: pass
    return "end"


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_agent_graph():
    """Build the full dual-pipeline LangGraph agent."""
    wf = StateGraph(AgentState)

    # ── Visibility Wrappers ────────────────────────────────────────────────────
    def wrap_node(node_fn, name):
        def wrapped(state: AgentState):
            with tracker.status_context(name):
                tracker.node_start(name)
                try:
                    res = node_fn(state)
                    # Specialized logic to update total chapters in tracker after planning
                    if name in ("planner", "discussion_planner") and res and "chapters" in res:
                        chapters = res.get("chapters", [])
                        if chapters:
                            tracker._total_chapters = len(chapters)
                            print(f"[tracker] Detected {len(chapters)} chapters. Monitoring progress...")
                    
                    tracker.node_done(name)
                    return res
                except Exception as e:
                    tracker.node_done(name, failed=True)
                    raise e
        return wrapped

    # Rewire nodes with wrappers
    wf.add_node("memory_init",         _memory_init_wrapper) # memory_init already has its own calls inside
    wf.add_node("scraper",             wrap_node(scraper_node, "scraper"))
    wf.add_node("test_case_gen",       wrap_node(test_case_node, "test_case_gen"))

    # Pipeline 1
    wf.add_node("planner",             wrap_node(planner_node, "planner"))
    wf.add_node("reflection",          wrap_node(reflection_node, "reflection"))
    wf.add_node("tts",                 wrap_node(tts_node, "tts"))
    wf.add_node("renderer",            wrap_node(renderer_node, "renderer"))

    # Pipeline 2
    wf.add_node("discussion_planner",  wrap_node(discussion_planner_node, "discussion_planner"))
    wf.add_node("multi_tts",           wrap_node(multi_tts_node, "multi_tts"))
    wf.add_node("dialogue_renderer",   wrap_node(dialogue_renderer_node, "dialogue_renderer"))

    # Shared
    wf.add_node("typography",          wrap_node(typography_node, "typography"))
    wf.add_node("animator",            wrap_node(animator_node, "animator"))
    wf.add_node("quality",             wrap_node(quality_node, "quality"))
    wf.add_node("thumbnail",           wrap_node(thumbnail_node, "thumbnail"))
    wf.add_node("stitcher",            wrap_node(stitcher_node, "stitcher"))
    
    # New Production Nodes
    wf.add_node("reasoning",           wrap_node(reasoning_node, "reasoning"))
    wf.add_node("semantic_engine",     wrap_node(semantic_engine_node, "semantic_engine"))
    wf.add_node("strategy_selector",   wrap_node(strategy_selector_node, "strategy_selector"))
    wf.add_node("motion_choreographer", wrap_node(motion_choreographer_node, "motion_choreographer"))

    # Cache-hit node
    def _cache_hit_node(state: AgentState) -> dict:
        import os, glob
        tracker.node_start("cache_hit") # Add temporary tracking if desired or skip
        cache_dir = state.get("cache_dir", "")
        mp4s = glob.glob(os.path.join(cache_dir, "*_final.mp4")) if cache_dir else []
        video_path = mp4s[0] if mp4s else state.get("final_video_path", "")
        print(f"[cache_hit] Returning existing video: {video_path}")
        tracker.node_done("cache_hit")
        return {"final_video_path": video_path, "error": ""}
    
    wf.add_node("cache_hit", _cache_hit_node)

    # ── Entry ──────────────────────────────────────────────────────────────────
    wf.set_entry_point("memory_init")
    wf.add_edge("memory_init", "scraper")

    # ── Architecture Selector (after scraper) ──────────────────────────────────
    wf.add_conditional_edges(
        "scraper", route_after_scraper,
        {
            "test_case_gen": "test_case_gen",
            "cache_hit": "cache_hit",
        },
    )
    wf.add_edge("cache_hit", END)

    # ── Main Flow (after test_case_gen) ────────────────────────────────────────
    wf.add_conditional_edges(
        "test_case_gen", route_after_test_case_gen,
        {
            "planner": "planner",
            "discussion_planner": "discussion_planner",
            "stitcher": "stitcher",
            "tts": "tts",
            "multi_tts": "multi_tts",
            "end": END,
        },
    )

    # ── Pipeline 1 edges ───────────────────────────────────────────────────────
    wf.add_conditional_edges(
        "planner", route_after_planner,
        {"reflection": "reflection", "end": END},
    )
    wf.add_conditional_edges(
        "reflection", route_after_reflection,
        {"planner": "planner", "semantic_engine": "semantic_engine"},
    )
    wf.add_edge("semantic_engine", "strategy_selector")
    wf.add_edge("strategy_selector", "motion_choreographer")
    wf.add_edge("motion_choreographer", "typography")
    wf.add_conditional_edges(
        "tts", route_after_tts,
        {"renderer": "renderer", "end": END},
    )
    wf.add_conditional_edges(
        "renderer", route_after_renderer,
        {"quality": "quality", "end": END},
    )

    # ── Pipeline 2 edges ───────────────────────────────────────────────────────
    wf.add_conditional_edges(
        "discussion_planner", route_after_discussion_planner,
        {"semantic_engine": "semantic_engine", "end": END},
    )
    wf.add_conditional_edges(
        "multi_tts", route_after_multi_tts,
        {"dialogue_renderer": "dialogue_renderer", "end": END},
    )
    wf.add_conditional_edges(
        "dialogue_renderer", route_after_dialogue_renderer,
        {"quality": "quality", "end": END},
    )

    # ── Shared edges (both pipelines converge here) ────────────────────────────
    # ── Parallel Branching after Typography ────────────────────────────
    wf.add_conditional_edges(
        "typography", 
        route_after_typography,
        {
            "animator": "animator", 
            "tts": "tts",
            "multi_tts": "multi_tts",
            "end": END
        }
    )

    # Both parallel branches (Visuals and Audio) converge on Renderer
    wf.add_edge("animator", "renderer")
    wf.add_edge("tts", "renderer")
    wf.add_edge("multi_tts", "renderer")

    # Pipeline 1 specific edges (already handled by router/edges above)
    # Pipeline 2 specific edges
    wf.add_conditional_edges(
        "dialogue_renderer", route_after_dialogue_renderer,
        {"quality": "quality", "end": END},
    )
    wf.add_conditional_edges(
        "quality", route_after_quality,
        {"thumbnail": "thumbnail"},
    )
    wf.add_conditional_edges(
        "thumbnail", route_after_thumbnail,
        {"stitcher": "stitcher"},
    )
    wf.add_conditional_edges(
        "stitcher", route_after_stitcher,
        {"end_success": END, "end": END},
    )

    return wf.compile()
