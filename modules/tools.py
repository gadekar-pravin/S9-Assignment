# modules/tools.py

from typing import List, Any, Optional

def summarize_tools(tools: List[Any]) -> str:
    """
    Creates a summarized string of tool descriptions.

    Args:
        tools (List[Any]): A list of tool objects, each expected to have 'name' and 'description' attributes.

    Returns:
        str: A formatted string summarizing each tool.
    """
    if not tools:
        return "No tools available."

    summary_lines = []
    for tool in tools:
        # Assuming the tool object has 'name' and 'description' attributes.
        summary_lines.append(f"- {tool.name}: {tool.description}")

    return "\n".join(summary_lines)

def filter_tools_by_hint(tools: List[Any], hint: Optional[str]) -> List[Any]:
    """
    Filters a list of tools based on a hint string.

    If a hint is provided, this function returns tools whose names are contained
    within the hint string. If the hint is None or empty, it returns all tools.

    Args:
        tools (List[Any]): A list of tool objects with a 'name' attribute.
        hint (Optional[str]): A string containing hints for tool selection.

    Returns:
        List[Any]: A filtered list of tool objects.
    """
    if not hint:
        return tools

    # Simple substring matching for now. Can be improved.
    return [tool for tool in tools if tool.name in hint]

def load_prompt(file_path: str) -> str:
    """
    Loads a prompt template from a file.

    Args:
        file_path (str): The path to the prompt file.

    Returns:
        str: The content of the file as a string.
    """
    with open(file_path, "r") as f:
        return f.read()
