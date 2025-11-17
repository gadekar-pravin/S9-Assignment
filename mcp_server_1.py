# mcp_server_1.py

import sys
import asyncio
from mcp.server.server import Server
from mcp.server.process import ProcessTransport
from mcp.common.tools import Tool, ToolResult
import math
from PIL import Image

# --- Tool Implementations ---

def add(a: int, b: int) -> ToolResult:
    """Adds two integers."""
    return ToolResult(content=[{"text": str(a + b)}])

def subtract(a: int, b: int) -> ToolResult:
    """Subtracts the second integer from the first."""
    return ToolResult(content=[{"text": str(a - b)}])

def multiply(a: int, b: int) -> ToolResult:
    """Multiplies two integers."""
    return ToolResult(content=[{"text": str(a * b)}])

def divide(a: int, b: int) -> ToolResult:
    """Divides the first integer by the second."""
    if b == 0:
        return ToolResult(content=[{"text": "Error: Division by zero"}], success=False)
    return ToolResult(content=[{"text": str(a / b)}])

def power(a: int, b: int) -> ToolResult:
    """Calculates the power of the first integer to the second."""
    return ToolResult(content=[{"text": str(a ** b)}])

def sin(a: float) -> ToolResult:
    """Calculates the sine of a number."""
    return ToolResult(content=[{"text": str(math.sin(a))}])

def cos(a: float) -> ToolResult:
    """Calculates the cosine of a number."""
    return ToolResult(content=[{"text": str(math.cos(a))}])

def tan(a: float) -> ToolResult:
    """Calculates the tangent of a number."""
    return ToolResult(content=[{"text": str(math.tan(a))}])

def factorial(n: int) -> ToolResult:
    """Calculates the factorial of a non-negative integer."""
    if n < 0:
        return ToolResult(content=[{"text": "Error: Factorial of a negative number"}], success=False)
    return ToolResult(content=[{"text": str(math.factorial(n))}])

def cbrt(a: float) -> ToolResult:
    """Calculates the cube root of a number."""
    return ToolResult(content=[{"text": str(a**(1/3))}])

def remainder(a: int, b: int) -> ToolResult:
    """Calculates the remainder of a division."""
    return ToolResult(content=[{"text": str(a % b)}])

def strings_to_chars_to_int(string: str) -> ToolResult:
    """Converts each character in a string to its ASCII integer value."""
    return ToolResult(content=[{"text": str([ord(c) for c in string])}])

def int_list_to_exponential_sum(numbers: list[int]) -> ToolResult:
    """Calculates the sum of exponentials for a list of integers."""
    return ToolResult(content=[{"text": str(sum([math.exp(i) for i in numbers]))}])

def fibonacci_numbers(n: int) -> ToolResult:
    """Generates the first n Fibonacci numbers."""
    if n <= 0:
        return ToolResult(content=[{"text": "[]"}])
    fib_list = [0, 1]
    while len(fib_list) < n:
        fib_list.append(fib_list[-1] + fib_list[-2])
    return ToolResult(content=[{"text": str(fib_list[:n])}])

def create_thumbnail(image_path: str, size: tuple[int, int] = (128, 128)) -> ToolResult:
    """
    Creates a thumbnail for an image.

    Args:
        image_path (str): The path to the input image.
        size (tuple[int, int]): The desired thumbnail size.

    Returns:
        ToolResult: The path to the saved thumbnail.
    """
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            thumbnail_path = "thumbnail.png"
            img.save(thumbnail_path, "PNG")
            return ToolResult(content=[{"text": f"Thumbnail saved to {thumbnail_path}"}])
    except Exception as e:
        return ToolResult(content=[{"text": f"Error creating thumbnail: {e}"}], success=False)

# --- Tool Definitions ---

tools = [
    Tool(name="add", description="Adds two integers.", func=add, schema={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}),
    Tool(name="subtract", description="Subtracts the second integer from the first.", func=subtract, schema={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}),
    Tool(name="multiply", description="Multiplies two integers.", func=multiply, schema={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}),
    Tool(name="divide", description="Divides the first integer by the second.", func=divide, schema={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}),
    Tool(name="power", description="Calculates the power of the first integer to the second.", func=power, schema={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}),
    Tool(name="sin", description="Calculates the sine of a number.", func=sin, schema={"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}),
    Tool(name="cos", description="Calculates the cosine of a number.", func=cos, schema={"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}),
    Tool(name="tan", description="Calculates the tangent of a number.", func=tan, schema={"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}),
    Tool(name="factorial", description="Calculates the factorial of a non-negative integer.", func=factorial, schema={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}),
    Tool(name="cbrt", description="Calculates the cube root of a number.", func=cbrt, schema={"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}),
    Tool(name="remainder", description="Calculates the remainder of a division.", func=remainder, schema={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}),
    Tool(name="strings_to_chars_to_int", description="Converts each character of a string to its ASCII integer value.", func=strings_to_chars_to_int, schema={"type": "object", "properties": {"string": {"type": "string"}}, "required": ["string"]}),
    Tool(name="int_list_to_exponential_sum", description="Calculates the sum of exponentials for a list of integers.", func=int_list_to_exponential_sum, schema={"type": "object", "properties": {"numbers": {"type": "array", "items": {"type": "integer"}}}, "required": ["numbers"]}),
    Tool(name="fibonacci_numbers", description="Generates the first n Fibonacci numbers.", func=fibonacci_numbers, schema={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}),
    Tool(name="create_thumbnail", description="Creates a thumbnail for an image.", func=create_thumbnail, schema={"type": "object", "properties": {"image_path": {"type": "string"}, "size": {"type": "array", "items": {"type": "integer"}}}, "required": ["image_path"]}),
]

async def main():
    """
    The main entry point for the MCP server.

    This function initializes and runs the MCP server, adding all the defined tools.
    It listens for requests via stdio if the '--stdio' argument is provided.
    """
    if len(sys.argv) > 1 and sys.argv[1] == '--stdio':
        server = Server(ProcessTransport(sys.stdin, sys.stdout))
        for tool in tools:
            server.add_tool(tool)
        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
