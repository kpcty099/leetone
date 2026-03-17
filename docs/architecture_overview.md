# LeetOne: Folder-per-Lambda Architecture

The project has been refactored into a modular, highly scalable "Folder-per-Lambda" architecture. Each major responsibility is isolated into its own "Lambda" module, containing its own node logic and supporting tools.

## Architecture Diagram

![Lambda Architecture Diagram](/C:/Users/HP/.gemini/antigravity/brain/6229d700-5afc-4caa-9f9e-15b08155808f/mermaid_diagram_final_1773574256850.png)

```mermaid
graph TD
    subgraph Orchestrator [LangGraph Orchestrator]
        State[(AgentState)]
        Graph[State Graph]
    end

    subgraph Scraper_Lambda [Scraper Lambda]
        SN[Scraper Node]
        ST[Playwright Tools]
    end

    subgraph Planner_Lambda [Planner Lambda]
        PN[Planner Node]
        RT[Reasoning Tools]
        MT[Multi-Tutor Node]
    end

    subgraph Visuals_Lambda [Visuals Lambda]
        VN[Typography Node]
        SE[Semantic Engine]
        SS[Strategy Selector]
        VJ[VLM Judge]
        VZ[Visualizers]
    end

    subgraph Animator_Lambda [Animator Lambda]
        AN[Animator Node]
        MW[Manim / Parallel Workers]
        GN[Grounding Node]
    end

    subgraph TTS_Lambda [TTS Lambda]
        TN[TTS Node]
        ET[Edge-TTS / ElevenLabs]
    end

    subgraph Renderer_Lambda [Renderer Lambda]
        RN[Renderer Node]
        RW[Renderer Workers]
        VR[Cinematic Renderer]
    end

    subgraph Post_Process_Lambda [Post-Process Lambda]
        SN_ST[Stitcher Node]
        QN[Quality Node]
        TH[Thumbnail Node]
    end

    %% Flow
    Graph --> SN
    SN --> Graph
    Graph --> PN
    PN --> Graph
    Graph --> SE
    SE --> SS
    SS --> VN
    VN --> Graph
    Graph --> AN
    AN --> Graph
    Graph --> TN
    TN --> Graph
    Graph --> RN
    RN --> Graph
    Graph --> SN_ST
    SN_ST --> END((Final Video))

    %% Dependencies
    Orchestrator -.-> |State Propagation| Scraper_Lambda
    Orchestrator -.-> |State Propagation| Planner_Lambda
    Orchestrator -.-> |State Propagation| Visuals_Lambda
```

## Module Responsibilities

| Lambda | Responsibility | Key Tools |
| :--- | :--- | :--- |
| **Scraper** | Fetches problem metadata, examples, and high-fidelity screenshots. | Playwright, LeetCode API |
| **Planner** | Generates the pedagogical video plan and scripts. | LLM (HuggingFace/OpenAI), Reasoning Engine |
| **Visuals** | Maps semantic concepts to visual strategies and branding. | VLM Choice Tree, Style Guides, Visualizers |
| **Animator** | Translates the plan into dynamic Manim animations. | Manim, Parallel Workers, Grounding Agent |
| **TTS** | Conversational voiceover generation. | Edge-TTS, ElevenLabs, Multi-Speaker Mixing |
| **Renderer** | Scene-level rendering and compositing. | MoviePy, CV2, Renderer Workers |
| **Post-Process** | Final assembly, quality scoring, and thumbnail creation. | FFmpeg, PIL, Quality Judge |

## End-to-End Status

> [!IMPORTANT]
> The architecture is fully integrated and modularized. Every node is now a dedicated "Lambda" with clearly defined boundaries. Standardizing imports across the `src.lambdas` namespace has resolved structural conflicts.

> [!WARNING]
> Final validation is in the "last mile" phase. I am currently resolving a silent termination in the Scraper node related to session state, which is the final blocker for full autonomous execution.
