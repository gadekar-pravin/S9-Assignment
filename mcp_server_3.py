# mcp_server_3.py

import sys
import asyncio
from duckduckgo_search import AsyncDDGS
from mcp.server.server import Server
from mcp.server.process import ProcessTransport
from mcp.common.tools import Tool, ToolResult
from trafilatura import fetch_url, extract

async def duckduckgo_search_results(query: str, max_results: int = 5) -> ToolResult:
    """
    Performs a web search using DuckDuckGo and returns the results.

    Args:
        query (str): The search query.
        max_results (int): The maximum number of results to return.

    Returns:
        ToolResult: A ToolResult containing a list of search results,
                    each with a title, URL, and snippet.
    """
    results = []
    async with AsyncDDGS() as ddgs:
        async for r in ddgs.text(query, max_results=max_results):
            results.append(r)
    return ToolResult(content=[{"text": str(results)}])

async def download_raw_html_from_url(url: str) -> ToolResult:
    """
    Downloads the main content of a webpage and returns it as clean text.

    This function uses trafilatura to fetch and extract the primary content
    from a URL, removing boilerplate like ads and navigation.

    Args:
        url (str): The URL of the webpage to download.

    Returns:
        ToolResult: A ToolResult containing the extracted text content.
    """
    downloaded = fetch_url(url)
    if not downloaded:
        return ToolResult(content=[{"text": "Failed to download URL."}], success=False)

    result = extract(downloaded, include_comments=False)
    if not result:
        return ToolResult(content=[{"text": "Failed to extract content."}], success=False)

    return ToolResult(content=[{"text": result}])


async def main():
    """
    The main entry point for the web search MCP server.

    This function initializes and runs the MCP server, providing tools for
    web search and content downloading.
    """
    if len(sys.argv) > 1 and sys.argv[1] == '--stdio':
        server = Server(ProcessTransport(sys.stdin, sys.stdout))

        search_tool = Tool(
            name="duckduckgo_search_results",
            description="Performs a web search using DuckDuckGo.",
            func=duckduckgo_search_results,
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {"type": "integer", "description": "Maximum number of results."}
                },
                "required": ["query"]
            }
        )
        server.add_tool(search_tool)

        download_tool = Tool(
            name="download_raw_html_from_url",
            description="Downloads and extracts the main content from a URL.",
            func=download_raw_html_from_url,
            schema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL to download."}},
                "required": ["url"]
            }
        )
        server.add_tool(download_tool)

        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
