# modules/action.py

from typing import Dict, Any, Union
from pydantic import BaseModel
import asyncio
import types
import json


# Optional logging fallback
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

class ToolCallResult(BaseModel):
    """
    Represents the result of a single tool call.

    Attributes:
        tool_name (str): The name of the tool that was called.
        arguments (Dict[str, Any]): The arguments passed to the tool.
        result (Union[str, list, dict]): The processed result of the tool call.
        raw_response (Any): The raw response from the tool.
    """
    tool_name: str
    arguments: Dict[str, Any]
    result: Union[str, list, dict]
    raw_response: Any

MAX_TOOL_CALLS_PER_PLAN = 5

async def run_python_sandbox(code: str, dispatcher: Any) -> str:
    """
    Executes a Python code string in a sandboxed environment.

    This function dynamically executes the provided code, which is expected
    to define an async `solve()` function. It injects a patched MCP client
    for handling tool calls and restricts the number of calls per plan.

    Args:
        code (str): A string containing the Python code for the `solve()` function.
        dispatcher (Any): An instance of a dispatcher for handling tool calls.

    Returns:
        str: The result of the `solve()` function, or an error string if execution fails.
    """
    print("[action] 🔍 Entered run_python_sandbox()")

    # Create a fresh module scope
    sandbox = types.ModuleType("sandbox")

    try:
        # Patch MCP client with real dispatcher
        class SandboxMCP:
            def __init__(self, dispatcher):
                self.dispatcher = dispatcher
                self.call_count = 0

            async def call_tool(self, tool_name: str, input_dict: dict):
                self.call_count += 1
                if self.call_count > MAX_TOOL_CALLS_PER_PLAN:
                    raise RuntimeError(f"Exceeded max tool calls ({MAX_TOOL_CALLS_PER_PLAN}) in solve() plan.")
                # REAL tool call now
                result = await self.dispatcher.call_tool(tool_name, input_dict)
                preview = ""
                if getattr(result, "content", None):
                    first = result.content[0]
                    preview_text = getattr(first, "text", "")
                    if isinstance(preview_text, str):
                        preview = preview_text[:120]
                log("sandbox", f"Tool '{tool_name}' returned preview: {preview!r}")
                return result

        sandbox.mcp = SandboxMCP(dispatcher)

        # Preload safe built-ins into the sandbox
        import json, re
        sandbox.__dict__["json"] = json
        sandbox.__dict__["re"] = re

        # Execute solve fn dynamically
        exec(compile(code, "<solve_plan>", "exec"), sandbox.__dict__)

        solve_fn = sandbox.__dict__.get("solve")
        if solve_fn is None:
            raise ValueError("No solve() function found in plan.")

        if asyncio.iscoroutinefunction(solve_fn):
            result = await solve_fn()
        else:
            result = solve_fn()

        # Clean result formatting
        if isinstance(result, dict) and "result" in result:
            return f"{result['result']}"
        elif isinstance(result, dict):
            return f"{json.dumps(result)}"
        elif isinstance(result, list):
            return f"{' '.join(str(r) for r in result)}"
        else:
            return f"{result}"






    except Exception as e:
        log("sandbox", f"⚠️ Execution error: {e}")
        return f"[sandbox error: {str(e)}]"
