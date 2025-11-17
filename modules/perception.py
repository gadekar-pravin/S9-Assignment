# modules/perception.py

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from modules.model_manager import ModelManager
from modules.tools import load_prompt
from core.context import AgentContext
import json

class PerceptionResult(BaseModel):
    """
    Represents the structured output of the perception phase.

    This class holds the AI's understanding of the user's intent,
    extracted entities, and suggestions for relevant tools and servers.

    Attributes:
        user_input (str): The original user input.
        intent (str): The perceived primary intent of the user.
        entities (List[str]): A list of key entities extracted from the input.
        tool_hint (str): A hint or suggestion for which tool might be useful.
        selected_servers (List[str]): A list of server IDs deemed relevant.
    """
    user_input: str
    intent: str
    entities: List[str]
    tool_hint: str
    selected_servers: List[str]

model = ModelManager()

async def run_perception(
    context: AgentContext,
    user_input: str,
    prompt_path: str = "prompts/perception_prompt.txt"
) -> PerceptionResult:
    """
    Analyzes the user's input to understand their intent and select relevant tools.

    This function uses a language model to process the user's query, along with
    descriptions of available tool servers, to produce a structured `PerceptionResult`.

    Args:
        context (AgentContext): The current agent context, containing server descriptions.
        user_input (str): The user's query or command.
        prompt_path (str): The file path to the perception prompt template.

    Returns:
        PerceptionResult: A structured representation of the perception analysis.
    """

    prompt_template = load_prompt(prompt_path)

    # Format server descriptions for the prompt
    server_descriptions_text = "\n".join(
        [f"- {s['id']}: {s['description']}" for s in context.mcp_server_descriptions]
    )

    formatted_prompt = prompt_template.format(
        user_input=user_input,
        server_descriptions=server_descriptions_text
    )

    raw_response = await model.generate_text(formatted_prompt)

    # Clean and parse the JSON response
    # The model sometimes wraps the JSON in ```json ... ```, so we strip that
    if raw_response.strip().startswith("```json"):
        json_str = raw_response.strip()[7:-4].strip()
    else:
        json_str = raw_response

    try:
        parsed_json = json.loads(json_str)
    except json.JSONDecodeError:
        # Handle cases where the model response is not valid JSON
        # This could involve logging the error and returning a default or error state
        raise ValueError("Failed to parse perception JSON from model response.")

    return PerceptionResult(
        user_input=user_input,
        **parsed_json
    )
