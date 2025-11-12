# MCP servers — what they are and why they’re useful

**Model Context Protocol (MCP)** defines a simple, typed way for an AI client (an LLM or an agent runtime) to talk to external “capability servers.” An **MCP server** exposes a catalog of capabilities—typically:

* **Tools** (RPC-like functions with typed inputs/outputs)
* **Resources** (read-only URIs the client can fetch, e.g., `greeting://alice`)
* **Prompts** (templated prompt snippets the client can request/use)

## Core functionality

* **Discovery:** The client connects and asks the server to enumerate available tools/resources/prompts.
* **Typed execution:** Tools accept/return structured data (often Pydantic models in Python), so the client can validate arguments and parse results reliably.
* **Stateless calls:** Calls are usually independent; the client sends an invocation and receives a result object that contains one or more content parts (e.g., text, image bytes).
* **Composable catalogs:** Multiple MCP servers can run side-by-side; the agent can pick the right tool set per task.

## Communication/transport

* **Transport:** MCP commonly runs over **stdio** (great for spawning helpers as subprocesses) and can also be implemented over sockets/web transports. In stdio mode the client launches the server executable, then exchanges JSON messages over the process’s stdin/stdout.
* **Message flow:** Typical lifecycle is `initialize → list_tools/resources/prompts → call_tool ... → close`. Results are returned as typed content (e.g., a JSON string in a `TextContent` payload).

## Typical use cases

* Give an LLM **skills** it doesn’t have out of the box (math, web search, RAG, file I/O).
* Keep tools **separate from the model runtime** (easier to update, test, permission, and scale).
* **Fan-out orchestration:** An agent can discover and call tools from several MCP servers while keeping its own logic simple.
* **Reproducibility & safety:** Typed schemas reduce prompt fragility and argument formatting errors.

---

# How MCP is implemented and used in this Python AI-Agent codebase

Below is how your repo wires MCP into an agent that plans calls, executes them, and iterates.

## 1) MCP servers in this repo

### `mcp_server_1.py` — Math & utility server

* Uses `FastMCP("Calculator")` and decorates many **tools**: arithmetic (`add`, `subtract`, …), trigonometry, `strings_to_chars_to_int`, `int_list_to_exponential_sum`, `fibonacci_numbers`, and an image utility `create_thumbnail`. Tools take/return **Pydantic models** imported from `models.py`.
* Also exposes a **resource**: `greeting://{name}` and two **prompts** (`review_code`, `debug_error`).
* Runs with **stdio transport** when started normally: `mcp.run(transport="stdio")`.

**Why it matters:** This server showcases canonical MCP primitives—typed tools, a resource URI, and prompts—ideal for deterministic agent/tool calling.

---

### `mcp_server_2.py` — Documents/RAG server

* Another `FastMCP` server exposing:

  * `search_stored_documents` (FAISS-backed semantic search over a local `/documents` corpus)
  * `convert_webpage_url_into_markdown` (cleans web pages to Markdown via `trafilatura`, replaces images with model-generated captions)
  * `extract_pdf` (PDF → Markdown via `pymupdf4llm`, with local image extraction & captioning)
* Includes a full **indexing pipeline**: chunking, LLM-aided semantic merging, embeddings (Ollama `nomic-embed-text`), FAISS index persistence, and a lazy `ensure_faiss_ready()` bootstrap.
* Starts the server (stdio) **and** proceeds to build/refresh the FAISS index in the same process.

**Why it matters:** This is your “knowledge access” capability. The agent can ask for web/PDF extraction and RAG results without baking that logic into the agent loop.

---

### `mcp_server_3.py` — Web search server

* `FastMCP("ddg-search")` with async tools:

  * `duckduckgo_search_results` (scrapes DDG HTML results with rate limiting)
  * `download_raw_html_from_url` (fetches and sanitizes page text)
* Demonstrates **async tools** and passing an MCP **`Context`** into tools for structured logging.

**Why it matters:** Gives the agent safe, rate-limited web search + fetch without mixing scraping logic into the agent core.

---

### `mcp_server_check.py` — Minimal client smoke test

* A tiny MCP client that:

  1. Starts `mcp_server_1.py` via stdio
  2. Calls `strings_to_chars_to_int("INDIA")`, parses the JSON string from `result.content[0].text`
  3. Feeds the ints to `int_list_to_exponential_sum` and prints a **FINAL_ANSWER**
* Useful for validating I/O and the JSON-parsing pattern your prompts expect.

---

## 2) Shared models for typed I/O

### `models.py`

* Central place for **Pydantic input/output models** used by tools (math ops, list/strings, RAG, web IO).
* The servers import these classes and annotate tool signatures; outputs always include a `result` field to keep downstream parsing uniform.

**Why it matters:** Strong typing prevents brittle agent calls and standardizes how tool responses are extracted.

---

## 3) How the agent discovers and calls MCP tools

### Configuration & strategy

* **`config/profiles.yaml`**

  * Declares a list of **MCP servers** (id, script path, cwd, description, and advertised capabilities).
  * Defines the agent’s **strategy** (e.g., `planning_mode: conservative`, max steps/lifelines), LLM selection, and memory settings.

### Client runtime & aggregation

* **`core/session.py`**

  * `MCP`: thin client that starts a single server (stdio) and makes a one-off call.
  * **`MultiMCP`**: the important piece. On `initialize()` it **spawns each configured server**, runs `list_tools()`, and builds a **global tool map** from tool name → server config.
  * On `call_tool(tool_name, arguments)`, it **locates the owning server** by name and spins a **fresh stdio session** for the call. This design keeps servers stateless per call and avoids long-lived connections.

### Planning → execution loop

* **`core/loop.py`**

  * Orchestrates each step:

    1. **Perception** chooses which servers are relevant (see below)
    2. Summarizes the selected tools’ descriptions for prompting
    3. Selects a **decision prompt** (conservative/exploratory)
    4. Asks the LLM to **generate a `solve()` function** that contains explicit `await mcp.call_tool('tool_name', {...})` calls
    5. Executes that `solve()` inside a sandbox (next point)
    6. Interprets the result: expects strings prefixed with `FINAL_ANSWER:` or `FURTHER_PROCESSING_REQUIRED:`, and loops if more processing is needed
* **`modules/action.py` → `run_python_sandbox`**

  * Builds a mini module scope and injects a small `SandboxMCP` that forwards `call_tool` to `MultiMCP`.
  * Enforces `MAX_TOOL_CALLS_PER_PLAN`.
  * Loads only minimal safe built-ins (`json`, `re`), then `exec`s the generated `solve()`.

**Why it matters:** The agent never hard-codes tool calls. Instead, it asks the LLM to produce a plan in code, then runs it safely with a strict tool budget and strongly typed calls.

---

## 4) How the agent picks which MCP servers to use

* **`modules/perception.py`**

  * Builds a prompt from the **server catalog** (id + description from `profiles.yaml`).
  * The LLM returns an `intent`, `entities`, and a **`selected_servers`** list.
  * If selection fails, it defaults to “all servers,” which is then **filtered** into a concise tool summary for the decision prompt.

* **`core/strategy.py`** and **`modules/decision.py`**

  * Choose the **decision prompt** template (`prompts/decision_prompt_*.txt`).
  * Generate the `solve()` body from the summarized tool catalog.
  * Prompts standardize critical patterns, e.g.:

    * Paste the **tool docstring** above the call
    * Always call by **string name**: `await mcp.call_tool('tool', input)`
    * Parse intermediate tool outputs using `json.loads(result.content[0].text)["result"]`
    * End with `FINAL_ANSWER:` or `FURTHER_PROCESSING_REQUIRED:`

**Why it matters:** This creates a consistent, verifiable contract between LLM-generated code and MCP servers.

---

## 5) Memory and session shaping the flow

* **`core/context.py`** initializes a **date-stamped session id** and wires in `MultiMCP` plus `mcp_server_descriptions`.
* **`modules/memory.py`** saves run metadata, tool calls, and results to a structured filesystem path (`memory/<yyyy>/<mm>/<dd>/session-...json`).
* There’s also a **Memory MCP server** stub in `modules/mcp_server_memory.py` (tools to query prior conversations), presently **commented out** in `profiles.yaml`. You can turn it on later to make past interactions queryable via MCP like any other capability.

---

## 6) Concrete request/response shape

A typical tool call (e.g., in `mcp_server_check.py`) looks like this from the client’s view:

1. `result = await session.call_tool("strings_to_chars_to_int", {"input": {"string": "INDIA"}})`
2. The client reads **text content** from `result.content[0].text` (a JSON string), then `json.loads(...)["result"]`.
3. That parsed value becomes the input to the next tool call.

This exact parsing pattern is enforced by your decision prompts so that every generated `solve()` is consistent.

---

## 7) End-to-end flow (put together)

1. **Startup** (`agent.py`):

   * Load `profiles.yaml` → build **server configs**
   * `MultiMCP.initialize()` → spawn each server via **stdio**, run `list_tools()`, build tool map
2. **User query arrives**
3. **Perception** → choose **server IDs**
4. **Planning** → LLM generates `solve()` with **explicit MCP tool calls**
5. **Execution** → sandbox runs `solve()`, which uses the injected `mcp.call_tool(...)` to talk through `MultiMCP` to the right server
6. **Tool server** executes the request and returns typed JSON content → agent parses → either

   * Returns **`FINAL_ANSWER:`** to the user, or
   * Uses **`FURTHER_PROCESSING_REQUIRED:`** to kick off another step with updated context
7. **Memory** logs the calls/results on disk

---

## Notable implementation details & suggestions

* **Transports:** All servers run with `mcp.run(transport="stdio")`. That’s ideal for local orchestration and avoids networking/ports.
* **Server identities:** `mcp_server_2.py` also names itself `"Calculator"` like `mcp_server_1.py`. Consider renaming to something like `"documents"` for clarity—it doesn’t affect functionality, but improves logs/diagnostics.
* **Schema hygiene:** `models.py` duplicates some classes (`UrlInput`, `MarkdownOutput`) near the bottom—worth deduplicating to avoid confusion.
* **Stateless calls:** `MultiMCP.call_tool` opens a **fresh** stdio session per call. That’s simple and robust; if you need high throughput, you could pool sessions per server.
* **Prompt discipline:** Your prompts guard against common LLM-tooling errors (wrong tool names, missing `FINAL_ANSWER:`, etc.). Keep those docstrings accurate so the model always pastes a correct “Usage” block.

---

## Quick mental mapping (file → role)

* **Servers (MCP providers)**

  * `mcp_server_1.py`: math/utils + resource + prompts
  * `mcp_server_2.py`: RAG/docs/webpage/PDF → Markdown; FAISS index
  * `mcp_server_3.py`: web search + fetch (DDG, httpx)

* **Clients/orchestration**

  * `core/session.py`: `MultiMCP` discovery and dispatch over stdio
  * `core/loop.py`: Think–plan–act loop (perception → plan → sandbox execute)
  * `modules/action.py`: sandbox execution with limited built-ins and MCP bridge
  * `modules/perception.py` / `core/strategy.py` / `modules/decision.py`: pick servers, build tool summaries, choose the right decision prompt, and generate `solve()`
  * `models.py`: Pydantic schemas for tool I/O
  * `config/profiles.yaml`: register servers, tuning strategy/LLM/memory
  * `agent.py`: CLI entrypoint tying it all together

---

### Bottom line

You’re using MCP exactly as intended: each capability lives behind a small, typed server; the agent discovers tools at runtime, asks the LLM to write a tiny plan that calls them, and then executes that plan in a guarded sandbox. The result is a clean separation of concerns, predictable tool I/O, and an agent that can grow by simply adding more MCP servers and updating `profiles.yaml`.
