# Gumbo

A visual, multi-step LLM workflow builder powered by Streamlit. Design
project pipelines with sequenced prompts, tool chains, and multi-model
orchestration — then compile everything into a polished document.

## Quick start

```bash
# Install dependencies
pip install streamlit pydantic anthropic openai requests beautifulsoup4

# Run the app
streamlit run gumbo/gumbo_ui.py
```

Open <http://localhost:8501> in your browser.

## Features

| Feature               | Description                                                     |
|-----------------------|-----------------------------------------------------------------|
| **Sequence tabs**     | Each tab is a workflow step with a main prompt + action items    |
| **Action items**      | Sub-tasks that chain context from prior steps                   |
| **Multi-model**       | Claude-3, GPT-4, Grok, or any custom model per task             |
| **Tool pipeline**     | Web Search, Code Execution, Browse Page, Image Viewer, PDF Search — tools run in sequence before the LLM call |
| **Run Tab / Run All** | Execute individual tabs or the full project with progress bars  |
| **Compile Project**   | Merge all tab outputs into a polished Markdown document         |
| **Undo**              | Restore accidentally removed tabs or action items               |
| **Save / Load**       | JSON persistence to disk + file upload/download                 |
| **Demo project**      | One-click "Life Tracker" with 5 tabs and 13 action items        |
| **Stub mode**         | Demo the full UI without API keys using simulated responses     |

## API keys

Add keys in the sidebar at runtime, or set environment variables:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # for Claude-3
export OPENAI_API_KEY="sk-..."          # for GPT-4
export XAI_API_KEY="xai-..."            # for Grok
# Optional — Web Search falls back to DuckDuckGo without these:
export GOOGLE_CSE_API_KEY="AIza..."
export GOOGLE_CSE_CX="a1b2c3..."
```

For deployed apps, use [Streamlit secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
in `.streamlit/secrets.toml`.

Toggle **Use real LLM APIs** in the sidebar to switch between real
calls and simulated stub responses.

## Architecture

```
gumbo/
  __init__.py
  models.py            # Pydantic data models + sample project factory
  engine.py            # WorkflowEngine: run_tab, run_project, compile_project
  gumbo_executors.py   # Real LLM clients, tool functions, retry logic
  storage.py           # JSON file persistence
  gumbo_ui.py          # Streamlit UI (main entry point)
  app.py               # Original lightweight entry point
  README.md            # This file
```

### Execution pipeline

```
User prompt
  |
  v
[Tool 1] -> [Tool 2] -> ... -> [Tool N]    (sequential tool pipeline)
  |
  v
Enriched prompt  =  prior context + tool outputs + original prompt
  |
  v
[LLM call]  (with automatic retry + exponential backoff)
  |
  v
Output  ->  stored on tab/subtask  ->  fed as context to next step
```

### Key modules

- **models.py** — `Project`, `SequenceTab`, `SubTask` Pydantic models.
  `create_sample_project()` builds the demo "Life Tracker".
- **engine.py** — `WorkflowEngine` with pluggable executor. `run_tab()` /
  `run_project()` drive sequential execution with progress callbacks.
  `compile_project()` merges existing outputs into a final document.
- **gumbo_executors.py** — Real tool functions (`web_search`, `code_execution`,
  `browse_page`, etc.) and LLM clients (Anthropic, OpenAI, xAI). All API
  calls retry up to 3 times with exponential backoff on transient errors.
- **gumbo_ui.py** — Full Streamlit front-end with sidebar config, dynamic
  tabs, undo stack, compile panel, and progress bars.

## Workflow

1. **Create** a project (or load the demo).
2. **Add tabs** — each is a workflow step (e.g. Research, Draft, Review).
3. **Write prompts** — main prompt per tab + action items for sub-tasks.
4. **Select LLM + tools** for each prompt.
5. **Run Tab** to execute one tab, or **Run All Tabs** for the full pipeline.
6. **Compile Project** to produce a polished Markdown document from all outputs.
7. **Download** the compiled result as `.md`.

## Error handling

- LLM API calls retry up to 3 times with exponential backoff (2s, 4s, 8s)
  on rate limits, timeouts, and server errors.
- Tool failures are caught and reported inline — the workflow continues.
- If an LLM call fails after all retries, the error message + any
  collected tool outputs are returned so the user can see what happened.
- All operations log to `stdout` via Python's `logging` module.

## License

See the project root LICENSE file.
