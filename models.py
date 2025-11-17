# models.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ToolExecution(BaseModel):
    """
    Represents a single execution of a tool within a session.

    Attributes:
        tool_name (str): The name of the tool that was executed.
        arguments (Dict[str, Any]): The arguments passed to the tool.
        result (Optional[Any]): The result returned by the tool.
    """
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None

class Session(BaseModel):
    """
    Represents a single interaction session with the agent.

    Attributes:
        session_id (str): A unique identifier for the session.
        user_input (str): The initial input from the user.
        tool_calls (List[ToolExecution]): A list of tool executions in the session.
        final_answer (Optional[str]): The final answer provided by the agent.
    """
    session_id: str
    user_input: str
    tool_calls: List[ToolExecution] = []
    final_answer: Optional[str] = None
