# modules/mcp_server_memory.py

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from datetime import datetime
from pathlib import Path
from mcp.server.server import Server
from mcp.server.process import ProcessTransport
from mcp.common.tools import Tool, ToolResult
from modules.model_manager import ModelManager
import time

try:
    from agent import log
except ImportError:
    def log(stage: str, msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

# --- Globals ---
INDEX_DIR = Path("memory_faiss_index")
INDEX_PATH = INDEX_DIR / "index.bin"
METADATA_PATH = INDEX_DIR / "metadata.json"
MEMORY_DIR = Path("memory")
POLL_INTERVAL = 5  # seconds

# Ensure directories exist
INDEX_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)

class MemoryServer:
    """
    A server that provides semantic search over the agent's long-term memory.

    This server indexes user questions and final answers from past sessions,
    allowing the agent to retrieve relevant historical context. It uses a FAISS index
    for efficient similarity search and automatically updates the index when new
    memory files are detected.

    Attributes:
        model (ModelManager): Manager for accessing embedding models.
        index (Optional[faiss.Index]): The FAISS index for vector search.
        metadata (List[Dict[str, Any]]): Metadata corresponding to the index entries.
        last_indexed_files (set): A set of file paths that have been indexed.
        lock (asyncio.Lock): A lock to prevent concurrent index modifications.
    """
    def __init__(self, model: ModelManager):
        """
        Initializes the MemoryServer.

        Args:
            model (ModelManager): An instance of ModelManager for generating embeddings.
        """
        self.model = model
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        self.last_indexed_files = set()
        self.lock = asyncio.Lock()
        self._load_index()

    def _load_index(self):
        """Loads the FAISS index and metadata from disk if they exist."""
        if INDEX_PATH.exists() and METADATA_PATH.exists():
            try:
                self.index = faiss.read_index(str(INDEX_PATH))
                with open(METADATA_PATH, "r") as f:
                    self.metadata = json.load(f)
                log("MemoryServer", f"✅ Loaded FAISS index with {self.index.ntotal} entries.")
                # Populate last_indexed_files from metadata
                self.last_indexed_files = {item['source_file'] for item in self.metadata}
            except Exception as e:
                log("MemoryServer", f"⚠️ Error loading index: {e}. Starting fresh.")
                self.index = None
                self.metadata = []
        else:
            log("MemoryServer", "No existing index found. Will create a new one.")

    async def _index_files(self, file_paths: List[Path]):
        """
        Indexes new memory files, creating or updating the FAISS index.

        Args:
            file_paths (List[Path]): A list of new memory file paths to index.
        """
        if not file_paths:
            return

        log("MemoryServer", f"Found {len(file_paths)} new memory files to index.")
        new_embeddings = []
        new_metadata = []

        for file_path in file_paths:
            try:
                with open(file_path, "r") as f:
                    session_data = json.load(f)

                user_query = None
                final_answer = None

                for item in session_data:
                    if item.get("type") == "run_metadata" and "user_query" in item:
                        user_query = item["user_query"]
                    if item.get("type") == "final_answer":
                        final_answer = item.get("final_answer", item.get("text"))

                if user_query and final_answer:
                    text_to_embed = f"User Question: {user_query}\nFinal Answer: {final_answer}"
                    embedding = await self.model.generate_embedding(text_to_embed)

                    new_embeddings.append(embedding)
                    new_metadata.append({
                        "source_file": str(file_path),
                        "user_query": user_query,
                        "final_answer": final_answer,
                        "timestamp": os.path.getmtime(file_path)
                    })
            except Exception as e:
                log("MemoryServer", f"⚠️ Error processing file {file_path}: {e}")

        if not new_embeddings:
            return

        embeddings_np = np.array(new_embeddings).astype('float32')
        if self.index is None:
            dimension = embeddings_np.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            log("MemoryServer", f"✨ Created new FAISS index with dimension {dimension}.")

        self.index.add(embeddings_np)
        self.metadata.extend(new_metadata)

        try:
            faiss.write_index(self.index, str(INDEX_PATH))
            with open(METADATA_PATH, "w") as f:
                json.dump(self.metadata, f, indent=2)
            log("MemoryServer", f"💾 Saved index with {self.index.ntotal} total entries.")
            # Update the set of indexed files
            self.last_indexed_files.update({str(p) for p in file_paths})
        except Exception as e:
            log("MemoryServer", f"⚠️ Error saving index: {e}")

    async def ensure_index_ready(self):
        """
        Checks for new memory files and updates the index if necessary.

        This method is called before a search to ensure the index is up-to-date.
        """
        async with self.lock:
            all_memory_files = set(str(p) for p in MEMORY_DIR.rglob("*.json"))
            new_files = [Path(p) for p in all_memory_files - self.last_indexed_files]

            if new_files:
                await self._index_files(new_files)

    async def search_historical_conversations(self, query: str, max_results: int = 5) -> ToolResult:
        """
        Performs a semantic search over the indexed historical conversations.

        Args:
            query (str): The search query.
            max_results (int): The maximum number of results to return.

        Returns:
            ToolResult: A ToolResult object containing the search results.
        """
        await self.ensure_index_ready()

        if self.index is None or self.index.ntotal == 0:
            return ToolResult(
                content=[{"text": "No historical conversations indexed yet."}],
                success=False
            )

        try:
            query_embedding = await self.model.generate_embedding(query)
            query_embedding_np = np.array([query_embedding]).astype('float32')

            k = min(max_results, self.index.ntotal)
            distances, indices = self.index.search(query_embedding_np, k)

            results = []
            for i in range(k):
                idx = indices[0][i]
                dist = distances[0][i]
                meta = self.metadata[idx]
                results.append({
                    "l2_distance": float(dist),
                    "user_query": meta["user_query"],
                    "final_answer": meta["final_answer"],
                    "source_file": meta["source_file"],
                    "timestamp": meta["timestamp"]
                })

            return ToolResult(
                content=[{"text": json.dumps(results)}],
                success=True
            )
        except Exception as e:
            log("MemoryServer", f"⚠️ Search error: {e}")
            return ToolResult(
                content=[{"text": f"An error occurred during search: {e}"}],
                success=False
            )


async def main():
    """The main entry point for the memory server process."""
    if len(sys.argv) > 1 and sys.argv[1] == '--stdio':
        log("MemoryServer", "🚀 Starting memory server with stdio transport...")

        model = ModelManager()
        memory_server = MemoryServer(model)

        server = Server(ProcessTransport(sys.stdin, sys.stdout))

        search_tool = Tool(
            name="search_historical_conversations",
            description="Search through historical conversations to find relevant information.",
            func=memory_server.search_historical_conversations,
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return."}
                },
                "required": ["query"]
            }
        )
        server.add_tool(search_tool)

        await server.serve()
    else:
        print("Usage: python modules/mcp_server_memory.py --stdio")

if __name__ == "__main__":
    asyncio.run(main())
