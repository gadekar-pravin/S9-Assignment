# modules/memory.py

import json
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import time
from datetime import datetime
from pydantic import BaseModel, Field

class MemoryItem(BaseModel):
    """
    A single entry in the agent's memory.

    Attributes:
        timestamp (float): The Unix timestamp of the memory item.
        type (str): The type of the memory item (e.g., 'user_input', 'tool_output').
        text (str): A human-readable description of the memory item.
        session_id (str): The ID of the session this item belongs to.
        tags (List[str]): A list of tags for categorization.
        tool_name (Optional[str]): The name of the tool, if applicable.
        tool_args (Optional[Dict[str, Any]]): The arguments passed to the tool.
        tool_result (Optional[Dict[str, Any]]): The result from the tool.
        success (Optional[bool]): Whether the tool call was successful.
        user_query (Optional[str]): The original user query that initiated the action.
        metadata (Dict[str, Any]): Any additional metadata.
    """
    timestamp: float
    type: str
    text: str
    session_id: str
    tags: List[str] = []

    # Tool-specific fields
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None

    # For linking back to user intent
    user_query: Optional[str] = None

    # Flexible metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryManager:
    """
    Manages the agent's long-term memory, storing and retrieving session data.

    This class handles the creation, saving, and loading of memory items for each
    session. Memories are stored as JSON files in a directory structure organized by date.

    Attributes:
        session_id (str): The unique identifier for the current session.
        base_dir (Path): The base directory where memories are stored.
        session_path (Path): The full path to the current session's memory file.
        session_items (List[MemoryItem]): The list of memory items for the current session.
    """
    def __init__(self, session_id: str, base_dir: str = "memory"):
        """
        Initializes the MemoryManager for a given session.

        Args:
            session_id (str): The ID for the session.
            base_dir (str): The root directory for memory storage.
        """
        self.session_id = session_id
        self.base_dir = Path(base_dir)
        self.session_path = self.base_dir / f"{session_id}.json"
        self.session_items: List[MemoryItem] = []

        # Ensure the directory for the session exists
        self.session_path.parent.mkdir(parents=True, exist_ok=True)

        self._load_session()

    def _load_session(self):
        """Loads existing session items from the session file, if it exists."""
        if self.session_path.exists():
            with open(self.session_path, "r") as f:
                try:
                    items_data = json.load(f)
                    self.session_items = [MemoryItem(**item) for item in items_data]
                except json.JSONDecodeError:
                    # Handle cases where the file might be empty or corrupt
                    self.session_items = []

    def _save_session(self):
        """Saves the current session's items to its JSON file."""
        with open(self.session_path, "w") as f:
            json.dump([item.dict() for item in self.session_items], f, indent=2)

    def add(self, item: MemoryItem):
        """
        Adds a new MemoryItem to the current session and saves it.

        Args:
            item (MemoryItem): The memory item to add.
        """
        self.session_items.append(item)
        self._save_session()

    def add_tool_output(
        self,
        tool_name: str,
        tool_args: Dict,
        tool_result: Any,
        success: bool,
        tags: Optional[List[str]] = None,
    ):
        """
        A convenience method for adding a tool output to memory.

        Args:
            tool_name (str): The name of the tool that was called.
            tool_args (Dict): The arguments passed to the tool.
            tool_result (Any): The result returned by the tool.
            success (bool): A flag indicating if the tool call was successful.
            tags (Optional[List[str]]): A list of tags for categorization.
        """
        text = f"Tool '{tool_name}' {'succeeded' if success else 'failed'}. Result: {tool_result}"

        item = MemoryItem(
            timestamp=time.time(),
            type="tool_output",
            text=text,
            session_id=self.session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            success=success,
            tags=tags or []
        )
        self.add(item)

    def get_session_items(self) -> List[MemoryItem]:
        """
        Retrieves all memory items for the current session.

        Returns:
            List[MemoryItem]: A list of all memory items.
        """
        return self.session_items
