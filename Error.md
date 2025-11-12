
## Root cause (two issues in `mcp_server_2.py`)

1. **Bad startup behavior**: `mcp_server_2.py` starts the stdio server in a **background thread** and then immediately calls `process_documents()` in the main thread. If `process_documents()` errors (very likely on a fresh repo: no documents, no local embedding server), the **main process crashes** and the stdio transport dies—so `MultiMCP.initialize()` can’t list tools and later calls to those tools fail.

2. **Undefined function** inside `process_documents()`: it calls `extract_webpage(...)`, but the actual tool/function is named `convert_webpage_url_into_markdown(...)`. That raises `NameError` on first run, which then triggers (1).

These two together explain why the math query sometimes works (it’s on `mcp_server_1.py`) but **web/PDF queries do not**.

---

## Fixes

### A) Run the server correctly (no side-effects on startup)

Make `mcp_server_2.py` follow the same pattern as your other servers: start **only** the stdio server in `__main__`. Let `search_stored_documents` lazily build the FAISS index via `ensure_faiss_ready()` when needed.

**File:** `mcp_server_2.py`

```diff
@@
 if __name__ == "__main__":
-    print("STARTING THE SERVER AT AMAZING LOCATION")
-
-    if len(sys.argv) > 1 and sys.argv[1] == "dev":
-        mcp.run() # Run without transport for dev server
-    else:
-        # Start the server in a separate thread
-        import threading
-        server_thread = threading.Thread(target=lambda: mcp.run(transport="stdio"))
-        server_thread.daemon = True
-        server_thread.start()
-        
-        # Wait a moment for the server to start
-        time.sleep(2)
-        
-        # Process documents after server is running
-        process_documents()
-        
-        # Keep the main thread alive
-        try:
-            while True:
-                time.sleep(1)
-        except KeyboardInterrupt:
-            print("\nShutting down...")
+    print("mcp_server_2.py starting")
+    if len(sys.argv) > 1 and sys.argv[1] == "dev":
+        mcp.run()  # Run without transport for dev server
+    else:
+        mcp.run(transport="stdio")  # Proper stdio mode, no extra threads/side-effects
+        print("\nShutting down...")
```

### B) Fix the typo in document processing (so lazy indexing won’t crash)

Replace the bad call to `extract_webpage(...)` with the correct `convert_webpage_url_into_markdown(...)`.

**File:** `mcp_server_2.py`

```diff
@@ def process_documents():
-            elif ext in [".html", ".htm", ".url"]:
-                mcp_log("INFO", f"Using Trafilatura to extract {file.name}")
-                markdown = extract_webpage(UrlInput(url=file.read_text().strip())).markdown
+            elif ext in [".html", ".htm", ".url"]:
+                mcp_log("INFO", f"Using Trafilatura to extract {file.name}")
+                # Use the correct function name defined above
+                markdown = convert_webpage_url_into_markdown(
+                    UrlInput(url=file.read_text().strip())
+                ).markdown
```

> Why both are needed: (B) prevents the latent `NameError` when FAISS is built lazily, and (A) prevents startup side-effects from crashing the stdio server before `MultiMCP` can list tools.

---

## (Nice-to-have) Small correctness fix in math server

Unrelated to the crash, but it will throw a validation error if ever used:

**File:** `mcp_server_1.py`

```diff
@@ def fibonacci_numbers(input: FibonacciInput) -> FibonacciOutput:
-    if n <= 0:
-        return FibonacciOutput(sequence=[])
+    if n <= 0:
+        return FibonacciOutput(result=[])
```

---

## How to verify

1. **Restart** your agent:

   ```bash
   python agent.py
   ```
2. Run a non-math query from your comments—for example:

   * “Summarize this page: [https://theschoolof.ai/”](https://theschoolof.ai/”)
   * “which course are we teaching on Canvas LMS? "H:\DownloadsH\How to use Canvas LMS.pdf"”
3. The agent should now perceive, plan, and call tools from `documents` (`mcp_server_2.py`) without the server crashing. Math queries continue to work.

This removes the framework-level blocker and lets the “other queries” in `agent.py` execute.
