# mcp_server_2.py

import os
import sys
import asyncio
from typing import List, Dict, Any, Optional
import json
import faiss
import numpy as np
from pathlib import Path
from mcp.server.server import Server
from mcp.server.process import ProcessTransport
from mcp.common.tools import Tool, ToolResult
from modules.model_manager import ModelManager
import pymupdf4llm
from trafilatura import fetch_url, extract
from markdownify import markdownify as md

# --- Document Indexing and RAG ---

class DocumentIndexer:
    """
    Manages the indexing and searching of documents for Retrieval-Augmented Generation (RAG).

    This class handles the creation of a FAISS index from documents in a specified directory.
    It can convert PDFs and web pages to text, generate embeddings, and perform semantic searches.

    Attributes:
        docs_dir (Path): The directory where source documents are stored.
        index_dir (Path): The directory for storing the FAISS index and metadata.
        index_path (Path): The path to the FAISS index file.
        metadata_path (Path): The path to the metadata file.
        model (ModelManager): The manager for accessing embedding models.
        index (Optional[faiss.Index]): The FAISS index.
        metadata (List[Dict[str, Any]]): Metadata for the indexed document chunks.
    """
    def __init__(self, docs_dir: str = "documents", index_dir: str = "faiss_index"):
        """
        Initializes the DocumentIndexer.

        Args:
            docs_dir (str): The directory containing source documents.
            index_dir (str): The directory to store the FAISS index.
        """
        self.docs_dir = Path(docs_dir)
        self.index_dir = Path(index_dir)
        self.index_path = self.index_dir / "index.bin"
        self.metadata_path = self.index_dir / "metadata.json"

        self.docs_dir.mkdir(exist_ok=True)
        self.index_dir.mkdir(exist_ok=True)

        self.model = ModelManager()
        self.index = None
        self.metadata = []

    async def initialize(self):
        """
        Initializes the indexer by loading an existing index or creating a new one.
        """
        if self.index_path.exists() and self.metadata_path.exists():
            self.load_index()
        else:
            await self.build_index()

    def load_index(self):
        """Loads the FAISS index and metadata from disk."""
        print("Loading existing FAISS index...")
        self.index = faiss.read_index(str(self.index_path))
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)
        print(f"Index loaded with {self.index.ntotal} vectors.")

    async def build_index(self):
        """Builds a new FAISS index from the documents in the documents directory."""
        print("Building new FAISS index...")
        all_chunks = []
        all_metadata = []

        for doc_path in self.docs_dir.iterdir():
            if doc_path.is_file():
                print(f"Processing document: {doc_path.name}")
                content = pymupdf4llm.to_markdown(doc_path)

                # Simple chunking by paragraph
                chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
                all_chunks.extend(chunks)
                all_metadata.extend([{"source": doc_path.name, "content": chunk} for chunk in chunks])

        if not all_chunks:
            print("No documents found to index.")
            return

        print(f"Generating embeddings for {len(all_chunks)} chunks...")
        embeddings = [await self.model.generate_embedding(chunk) for chunk in all_chunks]
        embeddings_np = np.array(embeddings).astype('float32')

        dimension = embeddings_np.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings_np)
        self.metadata = all_metadata

        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)

        print(f"Index built and saved with {self.index.ntotal} vectors.")

    async def search(self, query: str, k: int = 5) -> ToolResult:
        """
        Searches the document index for a given query.

        Args:
            query (str): The search query.
            k (int): The number of results to return.

        Returns:
            ToolResult: A ToolResult containing the search results.
        """
        if self.index is None:
            return ToolResult(content=[{"text": "Index not initialized."}], success=False)

        query_embedding = await self.model.generate_embedding(query)
        query_embedding_np = np.array([query_embedding]).astype('float32')

        distances, indices = self.index.search(query_embedding_np, k)

        results = []
        for i in range(k):
            idx = indices[0][i]
            results.append(self.metadata[idx])

        return ToolResult(content=[{"text": json.dumps(results)}])

def convert_webpage_to_markdown(url: str) -> ToolResult:
    """
    Fetches a webpage and converts its main content to Markdown.

    Args:
        url (str): The URL of the webpage.

    Returns:
        ToolResult: A ToolResult containing the Markdown content.
    """
    downloaded = fetch_url(url)
    if not downloaded:
        return ToolResult(content=[{"text": "Failed to download URL."}], success=False)

    result = extract(downloaded, include_comments=False)
    if not result:
        return ToolResult(content=[{"text": "Failed to extract content."}], success=False)

    markdown_content = md(result, heading_style="ATX")
    return ToolResult(content=[{"text": markdown_content}])

# --- Server Setup ---

async def main():
    """

    The main entry point for the document and web MCP server.

    This function initializes the DocumentIndexer and runs the MCP server with tools
    for document search and webpage conversion.
    """
    if len(sys.argv) > 1 and sys.argv[1] == '--stdio':
        indexer = DocumentIndexer()
        await indexer.initialize()

        server = Server(ProcessTransport(sys.stdin, sys.stdout))

        search_tool = Tool(
            name="search_stored_documents",
            description="Searches through stored documents to find relevant information.",
            func=indexer.search,
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "k": {"type": "integer", "description": "Number of results to return."}
                },
                "required": ["query"]
            }
        )
        server.add_tool(search_tool)

        webpage_tool = Tool(
            name="convert_webpage_url_into_markdown",
            description="Fetches a webpage and converts its main content to Markdown.",
            func=convert_webpage_to_markdown,
            schema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL of the webpage."}},
                "required": ["url"]
            }
        )
        server.add_tool(webpage_tool)

        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
