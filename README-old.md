# Cortex-R Agent (Session 9 Share)

> A reasoning-first AI agent that loops through perception → planning → tool execution while tapping into multiple MCP servers, a local RAG index, and persistent memory.

## Overview
- Interactive CLI (`agent.py`) asks what you want to solve, plans a `solve()` function, and runs it inside a sandbox so the LLM must think step-by-step.
- Uses **Multi-MCP orchestration** (`core/session.py`) to fan out to three tool servers: math/utility tools, document search & conversion, and web search/scraping.
- Has a **memory layer** (`modules/memory.py`) that stores every run, tool call, and answer under `memory/<date>/session-*.json` so sessions can be resumed or analyzed later.
- Ships with a **document ingestion + FAISS retrieval** pipeline (`mcp_server_2.py`) that converts anything in `documents/` into searchable embeddings.
- Prompts, strategies, model targets, and MCP wiring are plain-text configs in `config/` so junior engineers can tweak behavior without touching Python.

## Repository Tour
```text
.
├── agent.py                   # CLI entry point
├── core/                      # Session orchestration, strategy selection, contexts
├── modules/                   # Perception, planning, action, memory, model helpers
├── mcp_server_1.py            # Math & utility MCP server
├── mcp_server_2.py            # Document/RAG MCP server (FAISS + converters)
├── mcp_server_3.py            # DuckDuckGo + web scraper MCP server
├── config/                    # profiles.yaml (agent settings) + models.json (LLM targets)
├── documents/                 # Source files that get embedded for RAG
├── faiss_index/               # Generated FAISS index + metadata cache
├── memory/                    # Run history written per session
├── prompts/                   # Perception & decision prompt templates
├── uv.lock, pyproject.toml    # Dependency definitions
└── Notes.txt                  # Session notes from training
```

## Prerequisites
### Core software
- Python 3.11+ (matching `pyproject.toml`)
- Git and a terminal (PowerShell, cmd, bash, or zsh)
- [uv](https://github.com/astral-sh/uv) for creating/activating the virtual environment and installing dependencies (it bundles its own lightweight pip equivalent)

### External services & environment
- **Gemini API key** (model default). Export `GEMINI_API_KEY` or place it in a `.env`.
- **Ollama** running on `http://localhost:11434` with the models used in `mcp_server_2.py` (`phi4`, `gemma3:12b`, `qwen2.5:32b-instruct-q4_0`, `nomic-embed-text`). Install from [ollama.ai](https://ollama.ai/) and run `ollama serve` plus `ollama pull <model>`.
- Optional: If you switch to `ollama` models for text generation in `config/models.json`, make sure the model is downloaded before starting the agent.

### Data & storage
- Anything you want indexed belongs in `documents/`. PDFs, Word docs, markdown, and saved webpages are supported.
- FAISS artifacts live in `faiss_index/`. They are built automatically but the folder must be writable.
- The `memory/` folder should remain under version control so junior teammates can inspect previous sessions locally (commit only if redacting sensitive info).

## Installation
1. **Clone the project**
   ```bash
   git clone <your-fork-or-path>/s9.git
   cd "s9"
   ```

2. **Create & activate a virtual environment with uv**
   ```bash
   uv venv
   source .venv/bin/activate        # macOS/Linux
   # .venv\Scripts\activate         # Windows PowerShell/cmd
   ```

3. **Install dependencies with uv**
   ```bash
   uv pip install --upgrade pip
   uv pip install -e .
   ```
   > Quick path: `uv sync` reads `pyproject.toml` + `uv.lock`, creates the venv if missing, and installs everything in one command.

4. **Provide secrets in `.env` (or your shell profile)**
   ```bash
   cat <<'EOF' > .env
   GEMINI_API_KEY=sk-your-key-here
   EOF
   ```

5. **Download Ollama models (if you need the document server)**
   ```bash
   ollama pull phi4
   ollama pull gemma3:12b
   ollama pull qwen2.5:32b-instruct-q4_0
   ollama pull nomic-embed-text
   ```

6. **(Optional) Prime the FAISS index**
   - Place documents inside `documents/`.
   - Run `python mcp_server_2.py` once; it will chunk the docs, build embeddings, and save them under `faiss_index/`.

## Configuration
- `config/profiles.yaml`
  - `agent`: Display name/ID/description shown in logs.
  - `strategy`: `planning_mode`, `exploration_mode`, retries, and memory fallback behavior.
  - `memory`: Toggles persistent memory; `base_dir` and layout must match `MemoryManager`.
  - `llm`: Selects the **key** defined in `config/models.json`; defaults to `gemini`.
  - `mcp_servers`: Update each `cwd` to match **your** local path so subprocesses can find files. Enable/disable servers or add new ones here.
- `config/models.json`
  - Maps friendly keys (`gemini`, `phi4`, `gemma3:12b`, etc.) to the actual provider, REST endpoint, and embedding settings.
  - Switch the active model by changing `llm.text_generation` in `profiles.yaml`.
- `prompts/`
  - `perception_prompt.txt` and the decision prompts control how the LLM reasons about tools. Edit cautiously; keep JSON formats identical.
- `.env`
  - Store `GEMINI_API_KEY` (and any future secrets) so junior teammates can copy a template instead of editing shell profiles.

## Running & Testing
### 1. Start supporting services
- Run `ollama serve` in another terminal if you rely on local embeddings or captioning.
- Ensure `faiss_index/` exists for document search. If `faiss_index/index.bin` is missing, rerun `python mcp_server_2.py`.

### 2. Launch the agent CLI
```bash
python agent.py
```
- Type your task when prompted (`🧑 What do you want to solve today? →`).
- Enter `new` to reset the session while keeping the process running.
- Enter `exit` (or `Ctrl+C`) to quit cleanly.
- The agent prints each step, the perception result, the plan (a generated `solve()`), and the final answer.

### 3. Smoke-test individual MCP servers
- **Math tools**: `python mcp_server_check.py` (calls `strings_to_chars_to_int` and `int_list_to_exponential_sum`).
- **Document server**: `python mcp_server_2.py dev` starts it without stdio so you can watch indexing logs.
- **Web search server**: `python mcp_server_3.py dev` for manual testing; press `Ctrl+C` to stop.

### 4. Manual verification ideas
- Run a query that exercises each server (e.g., math → "Sum ASCII of INDIA", documents → "Search stored documents for Canvas", web → "Latest Tesla news").
- Inspect the newest file in `memory/<year>/<month>/<day>/` to confirm tool traces were persisted.

## Key Modules & Features
- `agent.py`: Terminal UI that wires everything together, loads the MCP profile, and keeps the session loop alive.
- `core/context.py`: Builds the `AgentContext`, injects persona/strategy, and logs events into Memory.
- `core/loop.py`: Implements the perception → planning → action loop, enforces max steps, and handles `FINAL_ANSWER` vs. `FURTHER_PROCESSING_REQUIRED`.
- `core/session.py`: `MultiMCP` scans each MCP server, caches tool metadata, and routes tool calls through stdio subprocesses.
- `core/strategy.py`: Chooses which decision prompt to use (conservative vs. exploratory) and can fall back to successful tools from memory.
- `modules/perception.py`: Calls the perception prompt to tag the intent and choose the best MCP servers.
- `modules/decision.py`: Builds an executable `solve()` plan using the selected decision prompt.
- `modules/action.py`: Runs the generated code in a **sandbox module**, counts tool calls, and forwards real tool executions through the dispatcher.
- `modules/memory.py`: Defines `MemoryItem` and `MemoryManager`, automatically storing run metadata, tool output, and final answers as JSON.
- `modules/model_manager.py`: Centralizes access to Gemini or Ollama models and keeps their settings in sync with `config/models.json`.
- `modules/mcp_server_memory.py`: Optional FastMCP server to expose historical chat logs through tools like `get_current_conversations`.
- `mcp_server_1.py`: FastMCP server containing math helpers, Fibonacci, ASCII conversions, and image thumbnailing.
- `mcp_server_2.py`: Document-focused server that converts PDFs/webpages to markdown, replaces images with captions, and runs FAISS search via embeddings produced by Ollama.
- `mcp_server_3.py`: DuckDuckGo search + raw HTML/text fetcher with rate limiting and BeautifulSoup cleanup.
- `documents/` → `faiss_index/`: Any file dropped here can be chunked and embedded; metadata is cached so unchanged files are skipped on re-index.
- `memory/`: Date-based folders containing every session so interns can replay tool histories during debugging.

## Document & Memory Workflow Tips
1. Drop new content into `documents/` (PDF, DOCX, markdown, text).
2. Rerun `python mcp_server_2.py` to refresh embeddings. The script hashes each file, so only changed docs are reprocessed.
3. Search from the agent by asking questions like “Search stored documents for Canvas LMS instructions”.
4. Inspect `faiss_index/metadata.json` to confirm your chunks and doc names look right.
5. For auditing, open the latest session JSON under `memory/`—each entry lists which tool ran, its arguments, success flag, and result snippet.

## Troubleshooting & Common Errors
- **`KeyError: 'GEMINI_API_KEY'` or blank LLM responses**  
  Set `GEMINI_API_KEY` in `.env` and reload your shell (`source .venv/bin/activate` re-reads `.env` via `python-dotenv` if you enable it, or export manually).

- **`requests.exceptions.ConnectionError: localhost:11434`**  
  Ollama is not running. Start it with `ollama serve` and ensure the referenced models are downloaded.

- **`faiss.IndexIOError: Error opening index.bin`**  
  The FAISS index is missing or corrupt. Delete `faiss_index/index.bin` and `metadata.json`, then run `python mcp_server_2.py` to rebuild.

- **`Tool 'XYZ' not found on any server` inside the agent loop**  
  Update the `cwd` paths in `config/profiles.yaml` so each MCP server runs from *this* repository. Then rerun `python agent.py` so `MultiMCP.initialize()` can rediscover the tools.

- **Sandbox error: `Exceeded max tool calls (5)`**  
  The generated `solve()` called more than five tools. Re-run the step or adjust `MAX_TOOL_CALLS_PER_PLAN` in `modules/action.py` after considering the safety trade-offs.

- **Memory files get `PermissionError`**  
  Ensure the `memory/` directory is writable. On Windows, avoid syncing it to OneDrive while the agent is running, or move `memory.storage.base_dir` elsewhere in `profiles.yaml`.

- **DuckDuckGo returns no results**  
  The HTML endpoint sometimes rate-limits. Wait a minute, reduce `max_results`, or rerun with a VPN if you suspect geographic blocking.

---
Need ideas or stuck during onboarding? Start by running `python mcp_server_check.py`, read the prompts in `prompts/`, and inspect a recent session file—those three activities reveal how the whole agent fits together. Once comfortable, adjust `strategy.planning_mode` or drop new reference docs to see how Cortex-R adapts. Happy hacking! 🧠✨
