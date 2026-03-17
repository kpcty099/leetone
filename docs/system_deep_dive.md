# LeetOne: Technical Deep-Dive

This document provides a master-level technical explanation of the LeetOne system, addressing design patterns, module logic, and quality control.

## 1. LLM Orchestration & Fallbacks

### Is there a LiteLLM Fallback?
The system utilizes a custom **LLM Factory** (`src/core/tools/llm_factory.py`) rather than the LiteLLM library, giving us granular control over prompt engineering and cost-tracking.

- **Structural Fallback:** The factory is designed to route between OpenAI, HuggingFace, and Gemini. If a provider fails, the system can be configured to "fail-over" to a secondary model.
- **Mock Fallback:** For development, a `USE_MOCKS` flag allows the system to run without any API costs, pulling from a local knowledge base of pre-generated responses.
- **Behavioral Fallback (Reflection):** Instead of a simple network fallback, we use a **Self-Correction Loop**. If the "Senior Architect" (`reflection_node`) finds issues in the plan, it retries the generation with specific feedback, ensuring logic-level reliability.

---

## 2. Core Design Patterns

| Pattern | Implementation in LeetOne |
| :--- | :--- |
| **Lambda Architecture** | Every node is a self-contained "Function as a Service" (FaaS) style module (e.g., `src/lambdas/tts`). |
| **Orchestrator** | **LangGraph** acts as the central brain, managing complex state transitions and conditional routing. |
| **Factory** | `llm_factory.py` abstracts the complexity of different AI providers (OpenAI vs. Gemini). |
| **Strategy** | The `Visual Strategy Selector` picks the best animation style (Pointer Motion vs. Tree Traversal) based on the problem. |
| **Bridge/Worker** | Parallelized Manim workers execute thousands of frames in isolation to speed up rendering. |
| **State Management** | A centralized `AgentState` (Pydantic/TypedDict) ensures every node has access to the "Universal Truth" of the current run. |

---

## 3. Module Deep-Dive

### Scraper Lambda (`src/lambdas/scraper`)
**The Eyes**: Uses Playwright to navigate LeetCode autonomously. It doesn't just grab text; it captures high-fidelity screenshots that are later used by the VLM Judge to ensure our video layout matches the source.

### Visuals Lambda (`src/lambdas/visuals`)
**The Artist**: This is the most complex visual stack. It includes a **VLM Choice Tree**.
- It generates 5 different layouts of a code block.
- It sends these to a Vision model (Gemini/GPT-4V).
- The model "picks" the most readable version (font size, padding, spacing) based on layout aesthetics.

### Robustness Lambda (`src/lambdas/robustness`)
**The Brakes**: This module contains the `test_case_node`. Before planning, it acts as a "QA Engineer" by finding the hardest edge cases (e.g., "What if the input array is empty?"). It forces the `Planner` to address these in the video script.

---

## 4. Quality Assurance (How we ensure Excellence)

We use a "Military Grade" approach to quality across three levels:

1.  **AI Peer Review (`reflection_node`):** A dedicated agent reviews the script before a single frame is rendered. If the justification score is < 8/10, the process is retracted and fixed.
2.  **Multimodal Validation (`vlm_judge`):** We don't guess if the text is too small; we use a Vision model to verify readability on a 1080p canvas.
3.  **Final Quality Audit (`quality_node`):** After rendering, every segment is scanned for:
    - **Audio Sync:** Is the MP3 present and valid?
    - **Visual Integrity:** Is the MP4 size correct (not a black screen)?
    - **Chapter Depth:** Does the video have all required sections (Dry Run, Brute Force)?

### Result:
Any video that completes the pipeline has been verified by at least **three different AI agents** and one **automated data auditor**.
