# Bug Fix Report – Infinite Loop Regression

## Summary
- **Issue**: Agent runs entered non-terminating loops on multi-hop inputs such as “summarize the contents of https://www.google.com” where the tool chain produced `FURTHER_PROCESSING_REQUIRED` responses.
- **Impact**: Sessions stalled after repeatedly issuing the same `convert_webpage_url_into_markdown` call and never reached a `FINAL_ANSWER`, exhausting user patience and leaving workflows incomplete (see `memory/2025/11/14/.../session-1763105557-31df8b.json:25` for an example of the repeated plan).
- **Fix status**: Multiple components were updated to ensure each stage sees the correct context, tools return schema-compliant payloads, and background services no longer spin indefinitely.

## Root Cause Analysis
1. **Planning ignored override input** (`core/loop.py:36-71`): when a tool returned `FURTHER_PROCESSING_REQUIRED`, we stored the synthesized follow-up prompt in `context.user_input_override`. Perception used that override, but planning still read the original `context.user_input`, so it kept producing the same `solve()` body and re-triggered the same tool forever.
2. **Prompt templating dropped step context** (`modules/decision.py:22-71`): we relied on `str.format()` with templates that contain literal braces (e.g., code blocks). This either raised `KeyError` or silently removed placeholders such as `{step_num}`. Without accurate step/memory metadata, the LLM could not differentiate between retries and kept emitting the same plan.
3. **Tool schema mismatch** (`mcp_server_1.py:143-152`): `fibonacci_numbers` returned `FibonacciOutput(sequence=[])`, which fails validation because the Pydantic model exposes `result`. Any plan that called this tool hit an exception, causing the dispatcher to retry the same plan in a loop.
4. **Document server bootstrap loop** (`mcp_server_2.py:338-414`): `process_documents()` invoked a helper (`extract_webpage`) that does not exist for `.html/.url` artifacts. The surrounding `while True` watchdog restarted ingestion after each crash, flooding the log and preventing the stdio server from making progress.
5. **Historical memory search re-scanned every JSON file** (`modules/mcp_server_memory.py:1-247`): each `search_historical_conversations` call synchronously walked the entire `memory/` tree and parsed every session history. On workspaces with thousands of entries this took minutes, so the agent timed out, retried the same tool, and appeared stuck in an infinite loop.

## Fix Implementation

### `core/loop.py`
- Introduced `effective_user_input` so both perception and planning consume the same override-aware prompt (`core/loop.py:36-71`).
- Added inline comment to highlight that the planning stage deliberately reuses the override, preventing divergence between perception and plan generation.

### `modules/decision.py`
- Replaced `str.format()` with deterministic placeholder replacement (`modules/decision.py:22-71`), ensuring literals like `{{` / `}}` survive and that `{step_num}`, `{max_steps}`, `{memory_texts}`, and `{tool_descriptions}` are always populated.
- This gives the LLM full context that subsequent steps are retries, which in testing eliminated the repeated `solve()` bodies that previously re-invoked the same tool.

### `mcp_server_1.py`
- Corrected `fibonacci_numbers` to return `FibonacciOutput(result=…)` even for non-positive `n` (`mcp_server_1.py:143-152`), preventing downstream validation errors that re-triggered planning retries.

### `mcp_server_2.py`
- Routed `.html/.url` ingestion through the existing `convert_webpage_url_into_markdown` helper (`mcp_server_2.py:341-347`), eliminating the NameError loop.
- Simplified the `__main__` block to rely on `mcp.run(transport="stdio")` without background threads or manual `while True` keep-alives (`mcp_server_2.py:407-414`), so the process terminates cleanly instead of spinning when ingestion fails.

### `modules/mcp_server_memory.py`
- Replaced the bespoke `MemoryStore` walker with a FAISS-backed semantic index:
  - Added configuration for `memory_faiss_index/` artifacts plus embedding service health checks (`modules/mcp_server_memory.py:1-80`).
  - Implemented `build_memory_index()` to extract Q/A pairs once and persist both vector data and metadata (`modules/mcp_server_memory.py:95-179`).
  - Updated `search_historical_conversations` to load the FAISS index, embed the query once, and return the top `k` matches with distances (`modules/mcp_server_memory.py:200-240`).
- Ensured the server pre-builds or refreshes the index during startup so that interactive searches stay below timeout thresholds (`modules/mcp_server_memory.py:181-247`).

## Verification Plan
1. **Regression scenario** – Re-run the recorded `convert_webpage_url_into_markdown` workflow (example in `memory/2025/11/14/.../session-1763105557-31df8b.json`) and confirm the follow-up step now receives the override prompt and reaches a `FINAL_ANSWER` after one extra tool call.
2. **Fibonacci contract** – Call `fibonacci_numbers` with `n = 0` and `n = 10` through the MCP harness to ensure the dispatcher receives schema-compliant payloads (`result=[]` / populated sequence) instead of triggering `ValidationError`.
3. **Memory search** – Launch `modules/mcp_server_memory.py` in stdio mode, issue multiple `search_historical_conversations` queries, and verify responses arrive within timeout (<1 s) with semantic matches.

*(When running these steps locally, re-run `process_documents` once to refresh FAISS artifacts and confirm `memory_faiss_index/*.json` are newer than the newest `memory/` file.)*
