# Cortex-R Architecture (Stakeholder Edition)

This document explains how every part of the Cortex-R repository works together, in business-friendly language. Use it to understand the moving pieces, trace the flow of information, and sketch diagrams with confidence.

---

## 1. Story of a User Request

1. **Conversation starts (`agent.py`)**  
   Someone types a question into the command-line console. The agent greets them and gets ready to think.

2. **Profile & tool directory are loaded (`config/profiles.yaml`)**  
   The agent learns who it is, how cautious it should be, which Large Language Model (LLM) to call, and where the helper tool servers live.

3. **Session context is created (`core/context.py`)**  
   A fresh session ID, date-stamped memory log, and bookkeeping fields (current step, task progress) are prepared so the run can be audited later.

4. **Perception step (`modules/perception.py`)**  
   The LLM reads the user question plus plain-language descriptions of every tool server. It reports the user’s intent, key entities, and which servers should be consulted.

5. **Planning step (`modules/decision.py`, `core/strategy.py`, `prompts/decision_*.txt`)**  
   With the shortlisted tools, the LLM writes a small Python function called `solve()`. This function describes which tools to call, in what order, and how to verify the result. The prompts make sure the plan ends with either `FINAL_ANSWER:` or a note that more work is needed.

6. **Action step (`modules/action.py`)**  
   The generated `solve()` function is executed inside a sandbox so it cannot harm the host machine. Calls to `mcp.call_tool()` are intercepted and routed through a dispatcher (`core/session.MultiMCP`), which spins up the right helper server for each tool call.

7. **Tool execution (`mcp_server_*.py`)**  
   Each Model Context Protocol (MCP) server exposes a catalog of typed tools—math, document retrieval, or web search. They receive structured requests, perform their specialist task, and return structured results.

8. **Memory, retries, and final answer (`modules/memory.py`)**  
   Every decision, tool call, and result is written to `memory/<date>/session-*.json`. If a plan fails, the agent can retry (lifelines) using past memory as hints. When the problem is solved, the answer is shown to the user and recorded.

---

## 2. System Building Blocks (Plain-English View)

### 2.1 User Interaction & Session Control
- **`agent.py`** is the only executable most people touch. It keeps the conversation loop running, forwards questions into the thinking pipeline, and prints final answers back to the screen.
- **`core/context.py`** builds the “pilot log” for each run: who asked what, which tools were tried, and whether they worked. It also attaches the dispatcher that knows how to talk to tool servers.
- **`core/loop.py`** is the step-by-step conductor. It enforces the maximum number of thinking rounds and lifelines per round and coordinates perception → planning → action in order.
- **`core/strategy.py`** chooses which planning prompt to use (cautious vs. exploratory) and can fall back to recently successful tools if the LLM gets stuck.

### 2.2 Thinking Modules
- **`modules/perception.py`**: asks the LLM to describe the request (intent, entities, recommended server IDs) using `prompts/perception_prompt.txt`.
- **`modules/decision.py`**: asks the LLM to write the `solve()` function. It uses the prompt path chosen by the strategy module and makes sure a complete function is produced.
- **`modules/action.py`**: runs `solve()` safely, limits tool calls, and injects a lightweight MCP client (`SandboxMCP`) so the generated plan can reach real tools without direct access to the host system.
- **`modules/tools.py`**: helper utilities for crafting prompts (summaries of tools, JSON extraction, etc.).
- **`modules/model_manager.py`**: the one place that knows how to talk to Gemini or, alternatively, local Ollama models. Changing model settings happens in `config/models.json` and `config/profiles.yaml`.
- **`modules/memory.py`**: defines what a memory item looks like and how to load/save the session log on disk.
- **`modules/mcp_server_memory.py`**: an optional MCP server that would let the agent search historical conversations as if they were another tool. It is currently disabled in the profile but ready for future use.

### 2.3 Tool Network (Model Context Protocol)
- **`core/session.MultiMCP`** maintains a registry of all tools exposed by every configured MCP server. For each call it spins up the target server via stdio, makes the request, and returns the response.
- **`mcp_server_1.py`** (“Math & utility server”) offers arithmetic, trigonometry, Fibonacci, ASCII conversion, thumbnail creation, and example prompts/resources. Great for numeric or quick string work.
- **`mcp_server_2.py`** (“Documents/RAG server”) ingests everything under `documents/`, builds FAISS search indexes, captions images, converts PDFs and web pages into Markdown, and answers semantic search queries.
- **`mcp_server_3.py`** (“Web search server”) wraps DuckDuckGo search and safe web-page fetching with rate limiting and content cleaning.
- **`mcp_server_check.py`** is a small diagnostic client that proves the math server works end-to-end.
- **`models.py`** houses the typed input/output schemas used by the MCP tools so that both agent and servers agree on the format.

### 2.4 Knowledge & Retrieval
- **`documents/`** contains the source material the document server can ingest (PDFs, Word files, markdown, text, saved web pages, and extracted images). Adding a file here makes it available to the retrieval system.
- **`faiss_index/`** stores the machine-readable search index produced by `mcp_server_2.py`. Keeping it on disk avoids rebuilding embeddings every run.
- **`memory/`** captures every session’s steps as JSON, organized by year/month/day folders for easy auditing.

### 2.5 Prompts & Guardrails
- **`prompts/perception_prompt.txt`** teaches the perception step how to describe the user request and pick servers.
- **`prompts/decision_prompt_*.txt`** (conservative, exploratory, sequential, parallel, sandbox variants) explain how `solve()` should be written, including usage examples for tool calls.
- These prompts are the “standard operating procedures” that keep the LLM grounded and reduce hallucinations.

### 2.6 Configuration & Dependencies
- **`config/profiles.yaml`** is the control tower for agent tuning: persona, planning mode, memory behavior, active LLM, and the list of MCP servers (with IDs, working directories, and descriptions).
- **`config/models.json`** defines the available LLMs and embedding models plus their endpoints or API keys.
- **`pyproject.toml`** lists Python dependencies and minimum versions.  
- **`uv.lock`** pins exact dependency versions to guarantee reproducible installs.

### 2.7 Documentation & Operational Notes
- **`README.md`** is the hands-on quick start.  
- **`Claude-README.md`** is a beginner-friendly developer guide with diagrams and troubleshooting steps.  
- **`MCP.md`** explains Model Context Protocol concepts and how this project implements them.  
- **`Bug-Fix-Report.md`** documents a prior production issue and the fixes that were applied.  
- **`Notes.txt`** contains session notes about heuristics and training discussions.

### 2.8 Generated or Supporting Folders
- **`__pycache__/`** folders hold compiled Python bytecode files created automatically for faster imports. They can be ignored for design purposes.
- **`prompts/decision_prompt_new.txt`** and **`prompts/decision_prompt.txt`** are legacy prompt drafts kept for experimentation.

---

## 3. Key Technical Concepts (Defined Simply)

- **Large Language Model (LLM)**: a text-based AI assistant. Here we default to Google’s Gemini model, but the setup also supports locally hosted Ollama models.
- **Model Context Protocol (MCP)**: a polite telephone system. The agent can connect to any MCP server, ask “what tools do you offer?”, and then call a tool with structured arguments. Each call is stateless and isolated.
- **Sandbox**: a safety bubble for executing the generated `solve()` function. It stops the plan from touching local files or running unlimited tools.
- **Embeddings & FAISS**: embeddings turn text into numbers so similar ideas end up near each other. FAISS is the catalog that lets us search those numbers quickly.
- **Memory Log**: a running diary of what the agent did (tools tried, outcomes, answers) saved to disk for auditing or future learning.

---

## 4. File & Module Reference

The table below summarizes every file or directory in the repository, its role, and its main connections. Grouped entries describe collections of similar files (e.g., all documents or all caches) because they play the same role.

| Path | Purpose & Functionality | Connections |
| --- | --- | --- |
| `agent.py` | Command-line entry point that loops over user questions, spins up agent sessions, and prints final answers. | Imports `core.loop.AgentLoop`, loads `config/profiles.yaml`, and passes tool configs into `core/session.MultiMCP`. |
| `core/context.py` | Builds session IDs, loads the agent profile, wires in the dispatcher, and logs run metadata. | Uses `modules.memory.MemoryManager` for storage and is referenced throughout the thinking loop. |
| `core/loop.py` | Controls the perception → planning → action cycle, enforcing max steps and lifelines. | Calls modules (`perception`, `decision`, `action`) and updates the context with outcomes. |
| `core/session.py` | Defines the MCP dispatcher (`MultiMCP`) that discovers tools and routes calls, plus a lightweight single-server helper. | Used by `agent.py`, `core/context`, and `modules/action` to reach tool servers. |
| `core/strategy.py` | Chooses the decision prompt based on planning mode, manages fallback behavior, and wraps `generate_plan`. | Referenced by `core/loop` before planning. |
| `modules/perception.py` | Runs the perception prompt to label user intent and pick relevant servers. | Called from `core/loop`; relies on `modules/model_manager` and `prompts/perception_prompt.txt`. |
| `modules/decision.py` | Crafts the full `solve()` function using the selected decision prompt. | Used by both `core/loop` and `core/strategy`. |
| `modules/action.py` | Executes the `solve()` code safely, injects a tool-budget-limited MCP client, and formats results. | Called from `core/loop`’s action phase; uses the dispatcher provided via context. |
| `modules/memory.py` | Defines the MemoryItem schema and handles loading/saving per-session JSON logs. | Instantiated in `core/context` and updated after each tool call in `core/loop`. |
| `modules/model_manager.py` | Manages configuration and API calls for Gemini or Ollama LLMs. | Imported by perception, decision, and strategy modules whenever text generation is required. |
| `modules/tools.py` | Prompt helper utilities: JSON extraction, tool summaries, filtering. | Used in perception and strategy prompts. |
| `modules/mcp_server_memory.py` | Optional MCP server exposing conversation history search tools. | Can be enabled by adding it back into `config/profiles.yaml`. |
| `models.py` | Shared Pydantic schemas describing inputs/outputs for all MCP tools (math, RAG, search). | Imported inside every `mcp_server_*.py` file to guarantee consistent data exchange. |
| `mcp_server_1.py` | MCP server hosting math, trigonometry, string conversion, and thumbnail tools plus example resources/prompts. | Listed as `math` in `config/profiles.yaml`; used via `MultiMCP`. |
| `mcp_server_2.py` | MCP server responsible for document ingestion, Markdown conversion, semantic chunking, image captioning, and FAISS search. | Listed as `documents` in the profile; reads from `documents/` and maintains `faiss_index/`. |
| `mcp_server_3.py` | MCP server for DuckDuckGo search and webpage scraping with rate limiting. | Listed as `websearch`; serves any question needing live web data. |
| `mcp_server_check.py` | Standalone script that calls the math server directly to verify tool behavior. | Useful during onboarding or debugging MultiMCP connectivity. |
| `config/profiles.yaml` | Main configuration file describing agent persona, planning settings, memory behavior, chosen LLM, and the MCP server catalog (IDs, scripts, descriptions, working directories). | Loaded at startup by `agent.py` and referenced to describe servers to the perception prompt. |
| `config/models.json` | Defines each supported LLM/embedding option (Gemini, Ollama, Nomic) along with API endpoints. | Consumed by `modules/model_manager.py`. |
| `prompts/perception_prompt.txt` | Text template instructing the LLM how to analyze the user question and pick servers. | Used exclusively by `modules/perception.py`. |
| `prompts/decision_prompt_conservative.txt`, `prompts/decision_prompt_exploratory_parallel.txt`, `prompts/decision_prompt_exploratory_sequential.txt`, `prompts/decision_prompt.txt`, `prompts/decision_prompt_new.txt` | Prompt playbooks that teach the LLM how to write `solve()` functions under different planning modes. Each file fine-tunes tone and sequencing. | Selected by `core/strategy` and fed into `modules/decision.generate_plan`. |
| `prompts/decision_prompt_new.txt` | Experimental version kept for future iterations. | Not referenced today but lives alongside official prompts. |
| `README.md` | Repository overview, quick start instructions, and troubleshooting tips. | Starting point for new contributors. |
| `Claude-README.md` | Extended developer guide with friendlier explanations and diagrams. | Helpful for onboarding less technical teammates. |
| `MCP.md` | Deep dive into the Model Context Protocol and how this project uses it. | Supports stakeholders who need to understand the tool layer. |
| `Bug-Fix-Report.md` | Postmortem describing a past issue in `mcp_server_2.py` and the applied fixes. | Captures institutional knowledge and serves as a cautionary tale. |
| `Notes.txt` | Session notes from Nov 8, 2025 about heuristics and assignments. | Provides historical context and rationale for current architecture choices. |
| `documents/` (folder) | Source knowledge base for the RAG pipeline. Notable files include `cricket.txt`, `DELETE_IMAGES.pdf`, `DLF_13072023190044_BRSR.pdf`, `dlf.md`, `economic.md`, `Experience Letter.docx`, `How to use Canvas LMS.pdf`, `INVG67564.pdf`, `markitdown.md`, `SAMPLE-Indian-Policies-and-Procedures-January-2023.docx`, and `Tesla_Motors_IP_Open_Innovation_and_the_Carbon_Crisis_-_Matthew_Rimmer.pdf`. Each file becomes searchable once ingested. | Read and processed by `mcp_server_2.py`; their content ultimately feeds `search_stored_documents`. |
| `documents/images/` | Stores images extracted during PDF or web conversion until they are captioned and deleted. | Used by `mcp_server_2.py` while generating Markdown. |
| `faiss_index/index.bin`, `faiss_index/metadata.json`, `faiss_index/doc_index_cache.json` | Machine-friendly search assets: the FAISS vector index, human-readable metadata per chunk, and a cache of file hashes. | Created/maintained by `mcp_server_2.py`; read by `search_stored_documents`. |
| `memory/<year>/<month>/<day>/session-*.json` | JSON transcripts of each agent session, capturing tool calls and answers. | Written by `modules/memory`; optional MCP memory server can expose them as tools. |
| `prompts/` (folder) | Houses every text prompt; already detailed above but listed to show their grouping. | Read by perception and decision modules. |
| `__pycache__/` folders (root and inside subpackages) | Auto-generated bytecode caches for Python modules. | No manual connections; safe to ignore unless cleaning build artifacts. |
| `pyproject.toml` | Declares the project name, Python version, and dependency list. | Used by `uv`/`pip` during installation. |
| `uv.lock` | Exact dependency lockfile for deterministic installs. | Read by `uv sync`. |

> **Note:** If additional `.json` files appear under `memory/` after running the agent, they follow the same structure and purpose described above.

---

## 5. Data Flow & Diagram Tips

To sketch this system:

1. **User → Agent (`agent.py`)**: show a single arrow entering the Perception/Decision/Action loop.  
2. **Loop Box**: inside it, draw three sub-boxes (Perception, Planning, Action) connected in order, with arrows to the memory store for logging.  
3. **Tool Layer**: from the Action box, draw a dispatcher node (`MultiMCP`) that fans out to the three MCP servers (Math, Documents, Web).  
4. **Knowledge Stores**: connect the Documents server to the `documents/` folder and FAISS index, and connect all servers back to the Action box returning results.  
5. **Outputs**: from the Action box draw arrows to both the user (final answer) and the `memory/` folder (audit trail).  
6. **Configuration & Prompts**: show `config/` and `prompts/` as reference inputs feeding into the perception and planning boxes.  
7. **Models**: depict the LLM (`modules/model_manager.py` + config) as a cloud that both Perception and Planning call for language understanding.

Following this guide gives stakeholders a clear picture of how questions move through Cortex-R, which files own each responsibility, and where to look when expanding capabilities.
