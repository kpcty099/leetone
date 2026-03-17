# LeetOne: System Manual & Operational Guide

This document explains how the finalized "Folder-per-Lambda" architecture works, how to execute the pipeline, and what to expect from the output.

## 1. Execution Workflow (How it Works)

The system uses a **LangGraph Orchestrator** to route data between specialized Lambda modules. Execution is split into two distinct pipelines based on problem difficulty.

### Node Processing Order

| Phase | Node | Description |
| :--- | :--- | :--- |
| **Ingestion** | `scraper` | Capture problem text and high-res screenshots from LeetCode. |
| **Logic** | `test_case_gen` | Generate algorithmic edge cases using LLM reasoning. |
| **Pipeline Switch**| **Router** | Routes to **Single Tutor** (Easy/Med) or **Multi-Tutor** (Hard). |
| **Planning** | `planner` / `discussion_planner` | Script the entire video (JSON plan with voiceover/visuals). |
| **Visuals** | `semantic_engine` | Analyze script to pick the best animations/visual strategies. |
| **Animation** | `animator` | Generate Manim code and execute parallel video workers. |
| **Audio** | `tts` / `multi_tts` | Generate professional voiceover using Edge or ElevenLabs. |
| **Rendering** | `renderer` / `dialogue_renderer` | Composites audio and animation into final chapters. |
| **Assembly** | `stitcher` | Joins chapters into a single high-quality video. |

---

## 2. Running the Pipeline

### Simple Run
```powershell
python src/main.py --problem "Two Sum"
```

### Force Regeneration (Bypass Cache)
```powershell
python src/main.py --problem "Two Sum" --regenerate true
```

### Problem Numbers
```powershell
python src/main.py --problem 1
```

---

## 3. Performance & Output Benchmarks

| Category | Typical Chapters | Est. Video Duration | Est. Gen Time |
| :--- | :---: | :---: | :---: |
| **Easy** | 3-4 | 1:30 - 3:00 min | 5-10 min |
| **Medium** | 4-6 | 3:00 - 5:00 min | 8-15 min |
| **Hard** | 8-10 | 8:00 - 12:00 min | 20-40 min |

> [!NOTE]
> Generation time varies based on LLM response speed and your CPU's ability to render Manim/MoviePy animations.

---

## 4. Why this Architecture? (Pros & Cons)

### The Good (Pros)
- **Scalability**: Each Lambda is self-contained. You can swap the TTS engine or the Scraper logic without touching the Animator.
- **Fail-Safe**: If the Animator fails on Chapter 5, the system saves the progress of Chapters 1-4. You don't lose the whole run.
- **Maintenance**: Clear responsibility. If there is a bug in the voiceover, you know exactly which folder to look in (`src/lambdas/tts`).
- **Interview Ready**: Shows deep understanding of decoupled services and state-driven agent orchestration.

### The Trade-offs (Cons)
- **Complexity**: Navigating 10+ folders can be overwhelming at first compared to a single script.
- **State Overhead**: Passing a large `AgentState` between nodes requires careful schema management.
- **Local Resources**: Rendering 12 minutes of video with Manim is CPU/GPU intensive.

---

## 5. Additional Features
- **Short-Term Memory (STM)**: Nodes share contextual data (like current run IDs) within a single execution.
- **Long-Term Memory (LTM)**: Successful runs are logged to centralized storage for future analytics and cache-hits.
- **Smart Caching**: The system detects existing final videos and bypasses all expensive nodes instantly.
