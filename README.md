# LeetOne: LeetCode Video Generator 🎬🤖

LeetOne is an autonomous pipeline designed to generate high-quality educational videos for LeetCode problems. It automates everything from problem scraping and solution planning to visual animation and final video rendering.

## 🚀 Features

- **Autonomous Agent Workflow**: Uses a graph-based agentic architecture to handle complex multi-step reasoning.
- **Dynamic Animation**: Generates programmatic animations to explain code logic visually.
- **Multi-Model Support**: Integrated with OpenAI, Gemini, and HuggingFace for reasoning and visual judgment.
- **Folder-per-Lambda Architecture**: Modular design for easy scalability and maintenance of individual pipeline stages.
- **Progress Tracking**: Built-in tracker to monitor the status of long-running generation tasks.

## 🛠️ Project Structure

- **`src/`**: Core source code.
    - **`main.py`**: Entry point for the application.
    - **`core/`**: Orchestration logic and state management.
    - **`lambdas/`**: Specialized modules (Animators, Planners, Reasoners, Scrapers, Renderers).
    - **`prompts/`**: AI agent prompt templates.
- **`config/`**: Provider and system configurations.
- **`docs/`**: Detailed system architecture and manuals.
- **`tests/`**: Automated smoke tests and pipeline validation scripts.

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kpcty099/leetone.git
   cd leetone
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the root directory and add your API keys:
   ```env
   OPENAI_API_KEY=your_key
   GEMINI_API_KEY=your_key
   HF_TOKEN=your_token
   ```

## 🎮 Usage

Run the pipeline by providing a LeetCode problem title or number:

```bash
python src/main.py --problem "Two Sum"
```

To bypass the cache and regenerate a video:
```bash
python src/main.py --problem 1 --regenerate True
```

## 🏗️ Architecture

The project follows a **Folder-per-Lambda** design, where each stage of the video generation process is isolated into its own "Lambda" module within `src/lambdas/`. This allows for independent testing and easier updates to specific parts of the pipeline (e.g., updating the animator without affecting the scraper).

---
Developed with ❤️ by the LeetOne Team.
