# mcp_server_check.py

import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def check_server(server_script: str):
    """
    Checks the status and available tools of a specified MCP server.

    This function launches an MCP server as a subprocess, connects to it via stdio,
    and lists its available tools. This is useful for debugging and ensuring that
    servers are correctly configured.

    Args:
        server_script (str): The path to the MCP server script to be checked.
    """
    print(f"--- Checking server: {server_script} ---")
    try:
        params = StdioServerParameters(
            command=sys.executable,
            args=[server_script, '--stdio'],
            cwd='.'
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Session initialized.")

                tools_result = await session.list_tools()
                print(f"🛠️  Available tools ({len(tools_result.tools)}):")
                for tool in tools_result.tools:
                    print(f"  - {tool.name}: {tool.description}")

                # Example tool call (if applicable and safe)
                # if 'add' in [tool.name for tool in tools_result.tools]:
                #     print("\n📞 Testing 'add(1, 2)'...")
                #     add_result = await session.call_tool('add', {'a': 1, 'b': 2})
                #     print(f"  Result: {add_result.content}")

    except Exception as e:
        print(f"❌ Error checking server {server_script}: {e}")
    finally:
        print(f"--- Finished checking {server_script} ---\n")

async def main():
    """
    The main entry point for the server check script.

    This function runs the server check for all three MCP servers.
    """
    await check_server("mcp_server_1.py")
    await check_server("mcp_server_2.py")
    await check_server("mcp_server_3.py")

if __name__ == "__main__":
    asyncio.run(main())
