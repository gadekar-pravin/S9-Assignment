# core/session.py

import os
import sys
from typing import Optional, Any, List, Dict
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCP:
    """
    A lightweight wrapper for one-time MCP tool calls using stdio transport.

    Each call to `list_tools` or `call_tool` spins up a new subprocess for the
    specified MCP server, establishes a session, performs the action, and then
    terminates cleanly. This approach is simple but may have higher overhead
    for frequent calls.

    Attributes:
        server_script (str): The name of the server script to execute.
        working_dir (str): The working directory for the server subprocess.
        server_command (str): The command to execute the server script (e.g., 'python').
    """

    def __init__(
        self,
        server_script: str = "mcp_server_2.py",
        working_dir: Optional[str] = None,
        server_command: Optional[str] = None,
    ):
        """
        Initializes the MCP wrapper.

        Args:
            server_script (str): The Python script for the MCP server.
            working_dir (Optional[str]): The working directory for the server. Defaults to the current directory.
            server_command (Optional[str]): The interpreter to run the script. Defaults to `sys.executable`.
        """
        self.server_script = server_script
        self.working_dir = working_dir or os.getcwd()
        self.server_command = server_command or sys.executable


    async def list_tools(self) -> List[Any]:
        """
        Lists the tools available on the configured MCP server.

        Returns:
            List[Any]: A list of tool definitions from the server.
        """
        server_params = StdioServerParameters(
            command=self.server_command,
            args=[self.server_script],
            cwd=self.working_dir
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return tools_result.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Calls a specific tool on the configured MCP server.

        Args:
            tool_name (str): The name of the tool to call.
            arguments (dict): The arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        server_params = StdioServerParameters(
            command=self.server_command,
            args=[self.server_script],
            cwd=self.working_dir
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=arguments)


class MultiMCP:
    """
    Manages connections to multiple MCP servers and dispatches tool calls.

    This class discovers tools from a list of server configurations and maintains
    a mapping of tools to their respective servers. When a tool is called, it
    establishes a short-lived session with the appropriate server to execute the call.

    Attributes:
        server_configs (List[dict]): A list of configurations for each MCP server.
        tool_map (Dict[str, Dict[str, Any]]): A mapping from tool names to their server and tool definitions.
        server_tools (Dict[str, List[Any]]): A mapping from server IDs to their list of tools.
    """

    def __init__(self, server_configs: List[dict]):
        """
        Initializes the MultiMCP dispatcher.

        Args:
            server_configs (List[dict]): A list of server configuration dictionaries.
        """
        self.server_configs = server_configs
        self.tool_map: Dict[str, Dict[str, Any]] = {}  # tool_name → {config, tool}
        self.server_tools: Dict[str, List[Any]] = {}  # server_name -> list of tools


    async def initialize(self):
        """
        Initializes the dispatcher by connecting to all configured servers
        to discover and map their available tools.
        """
        print("in MultiMCP initialize")
        for config in self.server_configs:
            try:
                params = StdioServerParameters(
                    command=sys.executable,
                    args=[config["script"]],
                    cwd=config.get("cwd", os.getcwd())
                )
                print(f"→ Scanning tools from: {config['script']} in {params.cwd}")
                async with stdio_client(params) as (read, write):
                    print("Connection established, creating session...")
                    try:
                        async with ClientSession(read, write) as session:
                            print("[agent] Session created, initializing...")
                            await session.initialize()
                            print("[agent] MCP session initialized")
                            tools = await session.list_tools()
                            print(f"→ Tools received: {[tool.name for tool in tools.tools]}")
                            for tool in tools.tools:
                                self.tool_map[tool.name] = {
                                    "config": config,
                                    "tool": tool
                                }
                                server_key = config["id"]
                                if server_key not in self.server_tools:
                                    self.server_tools[server_key] = []
                                self.server_tools[server_key].append(tool)
                    except Exception as se:
                        print(f"❌ Session error: {se}")
            except Exception as e:
                print(f"❌ Error initializing MCP server {config['script']}: {e}")

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Calls a tool by its name, routing the request to the correct server.

        Args:
            tool_name (str): The name of the tool to be called.
            arguments (dict): The arguments to be passed to the tool.

        Returns:
            Any: The result from the tool call.

        Raises:
            ValueError: If the tool name is not found in any of the servers.
        """
        entry = self.tool_map.get(tool_name)
        if not entry:
            raise ValueError(f"Tool '{tool_name}' not found on any server.")

        config = entry["config"]
        params = StdioServerParameters(
            command=sys.executable,
            args=[config["script"]],
            cwd=config.get("cwd", os.getcwd())
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments)

    async def list_all_tools(self) -> List[str]:
        """
        Returns a list of all tool names available across all servers.

        Returns:
            List[str]: A list of tool names.
        """
        return list(self.tool_map.keys())

    def get_all_tools(self) -> List[Any]:
        """
        Returns a list of all tool definitions from all servers.

        Returns:
            List[Any]: A list of tool objects.
        """
        return [entry["tool"] for entry in self.tool_map.values()]

    def get_tools_from_servers(self, selected_servers: List[str]) -> List[Any]:
        """
        Retrieves tool definitions for a specific list of server IDs.

        Args:
            selected_servers (List[str]): A list of server IDs.

        Returns:
            List[Any]: A list of tool definitions from the selected servers.
        """
        tools = []
        for server in selected_servers:
            if server in self.server_tools:
                tools.extend(self.server_tools[server])
        return tools



    async def shutdown(self):
        """A placeholder for shutdown logic, as sessions are not persistent."""
        pass
