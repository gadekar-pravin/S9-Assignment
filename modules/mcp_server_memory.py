from mcp.server.fastmcp import FastMCP
import faiss
import numpy as np
import requests
import json
import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ========================= CONFIG =========================
# --- FAISS/Embedding Config ---
ROOT = Path(__file__).parent.parent
MEMORY_DIR = ROOT / "memory"
INDEX_DIR = ROOT / "memory_faiss_index"
INDEX_DIR.mkdir(exist_ok=True)
INDEX_FILE = INDEX_DIR / "index.bin"
METADATA_FILE = INDEX_DIR / "metadata.json"

# --- Ollama Embedding Service Config ---
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM: Optional[int] = None
EMBED_SERVICE_READY = False


# ========================= MODELS =========================
class SearchInput(BaseModel):
    query: str
    max_results: int = Field(default=3, ge=1, le=10)


mcp = FastMCP("memory-service")


# ========================= HELPERS =========================
def mcp_log(msg: str):
    print(f"[memory-server] {msg}", file=sys.stderr)


def _request_embedding(text: str, timeout: float = 15.0) -> np.ndarray:
    """Low-level helper that calls the embedding service."""
    payload = {"model": EMBED_MODEL, "prompt": text}
    resp = requests.post(EMBED_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    vector = data.get("embedding")
    if vector is None:
        raise ValueError("Embedding service returned no vector.")
    return np.array(vector, dtype=np.float32)


def ensure_embedding_service(timeout: float = 5.0) -> bool:
    """Ping the embedding backend once so we can fail fast if it's offline."""
    global EMBED_SERVICE_READY, EMBED_DIM
    if EMBED_SERVICE_READY and EMBED_DIM:
        return True
    try:
        vec = _request_embedding("__memory_health_check__", timeout=timeout)
        EMBED_SERVICE_READY = True
        EMBED_DIM = vec.shape[0]
        mcp_log(f"Embedding service reachable (dim={EMBED_DIM}).")
        return True
    except Exception as exc:
        EMBED_SERVICE_READY = False
        EMBED_DIM = None
        mcp_log(f"Embedding service unavailable at {EMBED_URL}: {exc}")
        return False


def get_embedding(text: str) -> np.ndarray:
    """Gets a vector embedding for a text string."""
    global EMBED_SERVICE_READY, EMBED_DIM
    if not text.strip():
        text = "empty"  # Handle empty strings
    emb = _request_embedding(text, timeout=15.0)
    EMBED_SERVICE_READY = True
    EMBED_DIM = emb.shape[0]
    return emb


def get_latest_file_mtime(dir_path: Path) -> float:
    """Gets the modification time of the newest file in the directory tree."""
    max_mtime = 0.0
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".json"):
                mtime = (Path(root) / f).stat().st_mtime
                if mtime > max_mtime:
                    max_mtime = mtime
    return max_mtime


# ========================= INDEXING LOGIC =========================
def build_memory_index():
    """
    Builds a FAISS index from all conversation JSONs.
    Combines GPT-5's structured parsing with Grok's semantic indexing.
    """
    if not ensure_embedding_service():
        mcp_log("Skipping index rebuild until embedding service is available.")
        return

    mcp_log("Rebuilding historical conversation index...")
    embeddings = []
    metadata = []

    for json_path in MEMORY_DIR.rglob("session-*.json"):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                items = json.load(f)

            # Sort by timestamp to ensure correct Q&A order
            items.sort(key=lambda x: x.get("timestamp", 0.0))

            current_query = None
            current_intent = None
            current_query_time = 0.0

            for item in items:
                item_type = item.get("type")

                if item_type == "run_metadata":
                    text = item.get("text", "")
                    marker = "Started new session with input:"
                    if marker in text:
                        # This is a new user query. Store it.
                        query_text = text.split(marker, 1)[1].split(" at ", 1)[0].strip()
                        current_query = query_text
                        current_intent = item.get("intent")  # Store from metadata if present
                        current_query_time = item.get("timestamp", 0.0)

                elif item_type == "tool_output" and item.get("success") is True and current_query:
                    # This is a successful tool run *related* to the last query.
                    # Check if it's a final answer.
                    result_str = item.get("tool_result", {}).get("result", "")
                    if "FINAL_ANSWER:" in str(result_str):
                        final_answer = str(result_str).split("FINAL_ANSWER:", 1)[-1].strip()

                        # We have a full Q&A pair. Index it.
                        full_text_to_embed = f"User: {current_query}\nAgent: {final_answer}"

                        # Get embedding
                        try:
                            emb = get_embedding(full_text_to_embed)
                        except Exception as embed_err:
                            mcp_log(f"Embedding failed while indexing {json_path}: {embed_err}")
                            return
                        embeddings.append(emb)

                        # Store the structured data as metadata
                        metadata.append({
                            "user_query": current_query,
                            "final_answer": final_answer,
                            "intent": current_intent,
                            "source_file": str(json_path.relative_to(ROOT)),
                            "timestamp": item.get("timestamp", 0.0)
                        })

                        # Clear current query to avoid duplicate answers for one query
                        current_query = None

        except Exception as e:
            mcp_log(f"Failed to parse {json_path}: {e}")

    if embeddings:
        # Create and save the FAISS index
        dim = embeddings[0].shape[0]
        index = faiss.IndexFlatL2(dim)
        index.add(np.stack(embeddings))
        faiss.write_index(index, str(INDEX_FILE))

        # Save the metadata
        METADATA_FILE.write_text(json.dumps(metadata, indent=2))
        mcp_log(f"Successfully indexed {len(metadata)} Q&A pairs.")
    else:
        mcp_log("No Q&A pairs found to index.")


def ensure_index_ready():
    """Checks if the index exists and is up-to-date, rebuilding if necessary."""
    if not INDEX_FILE.exists() or not METADATA_FILE.exists():
        mcp_log("Index not found. Building for the first time...")
        build_memory_index()
        return

    # Check if any memory files are newer than the index
    index_mtime = INDEX_FILE.stat().st_mtime
    latest_file_mtime = get_latest_file_mtime(MEMORY_DIR)

    if latest_file_mtime > index_mtime:
        mcp_log("Conversation history is newer than index. Rebuilding...")
        build_memory_index()
    else:
        mcp_log("Index is up-to-date.")


# ========================= MCP TOOL =========================
@mcp.tool()
def search_historical_conversations(input: SearchInput) -> Dict[str, Any]:
    """
    Semantically search all past conversations with the agent.
    Usage: input={"input": {"query": "what we discussed about Databricks", "max_results": 3}}
    result = await mcp.call_tool('search_historical_conversations', input)
    """
    try:
        ensure_index_ready()  # Ensure index is ready before searching

        if not INDEX_FILE.exists():
            return {"result": {"matches": [], "message": "No history indexed."}}

        # Load index and metadata
        index = faiss.read_index(str(INDEX_FILE))
        meta = json.loads(METADATA_FILE.read_text())

        # Get embedding for the user's query
        q_vec = get_embedding(input.query).reshape(1, -1)

        # Perform FAISS search
        distances, indices = index.search(q_vec, input.max_results)

        results = []
        for i, dist in zip(indices[0], distances[0]):
            if 0 <= i < len(meta):
                match = meta[i]
                match["l2_distance"] = float(dist)  # Add distance score
                results.append(match)

        # Return matches in the standard "result" wrapper
        return {
            "result": {
                "query": input.query,
                "matches": results,
                "count": len(results)
            }
        }
    except Exception as e:
        mcp_log(f"Error during search: {e}")
        return {"result": {"status": "error", "message": str(e), "matches": []}}


# ========================= SERVER START =========================
if __name__ == "__main__":
    mcp_log("Starting memory server...")
    ensure_index_ready()  # Build index on first launch
    mcp.run(transport="stdio")
