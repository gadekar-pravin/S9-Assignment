# core/context.py

from typing import List, Optional, Dict, Any
from modules.memory import MemoryManager, MemoryItem
from core.session import MultiMCP  # For dispatcher typing
from pathlib import Path
import yaml
import time
import uuid
from datetime import datetime
from pydantic import BaseModel

class StrategyProfile(BaseModel):
    """
    Defines the operational strategy for the AI agent.

    Attributes:
        planning_mode (str): The primary planning mode, e.g., 'conservative' or 'exploratory'.
        exploration_mode (Optional[str]): The sub-mode for exploration, e.g., 'parallel' or 'sequential'.
        memory_fallback_enabled (bool): Whether to use memory for fallback suggestions.
        max_steps (int): The maximum number of steps the agent can take.
        max_lifelines_per_step (int): The number of retries allowed per step.
    """
    planning_mode: str
    exploration_mode: Optional[str] = None
    memory_fallback_enabled: bool
    max_steps: int
    max_lifelines_per_step: int


class AgentProfile:
    """
    Contains the configuration and persona for the AI agent.

    This class loads its settings from 'config/profiles.yaml'.
    """
    def __init__(self):
        """Initializes the AgentProfile by loading from the YAML configuration."""
        with open("config/profiles.yaml", "r") as f:
            config = yaml.safe_load(f)

        self.name: str = config["agent"]["name"]
        self.id: str = config["agent"]["id"]
        self.description: str = config["agent"]["description"]

        self.strategy = StrategyProfile(**config["strategy"])
        self.memory_config: Dict[str, Any] = config["memory"]
        self.llm_config: Dict[str, Any] = config["llm"]
        self.persona: Dict[str, Any] = config["persona"]


    def __repr__(self):
        """Provides a string representation of the AgentProfile."""
        return f"<AgentProfile {self.name} ({self.strategy})>"

class AgentContext:
    """
    Holds all session state, including user input, memory, and strategies.

    Attributes:
        user_input (str): The initial user input for the session.
        agent_profile (AgentProfile): The configuration profile for the agent.
        memory (MemoryManager): The memory manager for the session.
        session_id (str): The unique identifier for the session.
        dispatcher (Optional[MultiMCP]): The dispatcher for MCP tool calls.
        mcp_server_descriptions (Optional[List[Any]]): Descriptions of available MCP servers.
        step (int): The current step number in the agent's process.
        task_progress (List[Dict[str, Any]]): A log of subtasks and their statuses.
        final_answer (Optional[str]): The final answer, once determined.
    """

    def __init__(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        dispatcher: Optional[MultiMCP] = None,
        mcp_server_descriptions: Optional[List[Any]] = None,
    ):
        """
        Initializes the AgentContext for a new session.

        Args:
            user_input (str): The user's query or command.
            session_id (Optional[str]): An existing session ID to resume. If None, a new one is created.
            dispatcher (Optional[MultiMCP]): The tool dispatcher for the session.
            mcp_server_descriptions (Optional[List[Any]]): Descriptions of available MCP servers.
        """
        if session_id is None:
            today = datetime.now()
            ts = int(time.time())
            uid = uuid.uuid4().hex[:6]
            session_id = f"{today.year}/{today.month:02}/{today.day:02}/session-{ts}-{uid}"

        self.user_input = user_input
        self.agent_profile = AgentProfile()
        self.memory = MemoryManager(session_id=session_id)
        self.session_id = self.memory.session_id
        self.dispatcher = dispatcher
        self.mcp_server_descriptions = mcp_server_descriptions
        self.step = 0
        self.task_progress: List[Dict[str, Any]] = []
        self.final_answer: Optional[str] = None


        # Log session start
        self.add_memory(MemoryItem(
            timestamp=time.time(),
            text=f"Started new session with input: {user_input} at {datetime.utcnow().isoformat()}",
            type="run_metadata",
            session_id=self.session_id,
            tags=["run_start"],
            user_query=user_input,
            metadata={
                "start_time": datetime.now().isoformat(),
                "step": self.step
            }
        ))

    def add_memory(self, item: MemoryItem):
        """
        Adds a MemoryItem to the session's memory.

        Args:
            item (MemoryItem): The memory item to add.
        """
        self.memory.add(item)

    def format_history_for_llm(self) -> str:
        """
        Formats the history of tool calls for inclusion in a large language model prompt.

        Note:
            This method references `self.tool_calls`, which is not a standard attribute
            of this class. It may be part of an earlier design or intended for dynamic assignment.
            As such, it may raise an AttributeError if `tool_calls` is not set.

        Returns:
            str: A formatted string of the tool call history, or "No previous actions" if none exist.
        """
        if not hasattr(self, 'tool_calls') or not self.tool_calls:
            return "No previous actions"

        history = []
        for i, trace in enumerate(self.tool_calls, 1):
            result_str = str(trace.result)
            if i < len(self.tool_calls):  # Previous steps
                if len(result_str) > 50:
                    result_str = f"{result_str[:50]}... [RESPONSE TRUNCATED]"
            # else: last step gets full result

            history.append(f"{i}. Used {trace.tool_name} with {trace.arguments}\nResult: {result_str}")

        return "\n\n".join(history)

    def log_subtask(self, tool_name: str, status: str = "pending"):
        """
        Logs the start of a new subtask or tool call.

        Args:
            tool_name (str): The name of the tool or subtask.
            status (str): The initial status, defaults to "pending".
        """
        self.task_progress.append({
            "step": self.step,
            "tool": tool_name,
            "status": status,
        })

    def update_subtask_status(self, tool_name: str, status: str):
        """
        Updates the status of an existing subtask.

        Args:
            tool_name (str): The name of the tool or subtask to update.
            status (str): The new status, e.g., "success" or "failure".
        """
        for item in reversed(self.task_progress):
            if item["tool"] == tool_name and item["step"] == self.step:
                item["status"] = status
                break

    def __repr__(self):
        """Provides a string representation of the AgentContext."""
        return f"<AgentContext step={self.step}, session_id={self.session_id}>"
