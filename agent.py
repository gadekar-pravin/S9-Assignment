# agent.py

import os
import sys
import asyncio
import yaml
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.context import AgentContext
from core.loop import AgentLoop
from core.session import MultiMCP
from heuristic_rules import apply_input_heuristics
from modules.tools import summarize_tools

# --- Global MCP Dispatcher ---
# This will be initialized asynchronously in main
mcp_dispatcher: Optional[MultiMCP] = None

def log(stage: str, msg: str):
    """
    A simple logging function to print messages with a timestamp and stage.

    Args:
        stage (str): The stage of the agent's process (e.g., 'init', 'perception').
        msg (str): The message to be logged.
    """
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage.upper()}] {msg}")

async def get_selectively_injected_context(user_input: str, max_results: int = 2, distance_threshold: float = 300.0) -> str:
    """
    Retrieves relevant historical context to inject into the user's prompt.

    This function calls the memory server to find past conversations similar to the
    current user input. If relevant results are found below a distance threshold,
    it formats them for inclusion in the prompt.

    Args:
        user_input (str): The user's current input.
        max_results (int): The maximum number of historical items to retrieve.
        distance_threshold (float): The maximum L2 distance for a result to be considered relevant.

    Returns:
        str: A string of formatted historical context, or an empty string if none is found.
    """
    global mcp_dispatcher
    if not mcp_dispatcher:
        return ""

    try:
        # 1. Search for relevant historical conversations
        history_result = await mcp_dispatcher.call_tool(
            'search_historical_conversations',
            {"query": user_input, "max_results": max_results}
        )

        # 2. Check if the call was successful and if there's content
        if not history_result.success or not history_result.content:
            return ""

        # The result is a JSON string in the first content item
        qa_pairs = json.loads(history_result.content[0]['text'])

        # 3. Filter by distance threshold
        relevant_pairs = [
            pair for pair in qa_pairs
            if pair.get('l2_distance', float('inf')) < distance_threshold
        ]

        if not relevant_pairs:
            return ""

        # 4. Format for injection
        formatted_context = "Relevant past conversations for context:\n"
        for pair in relevant_pairs:
            formatted_context += f"- User asked: '{pair['user_query']}'\n"
            formatted_context += f"  Agent answered: '{pair['final_answer']}'\n"

        log("context", f"Injecting {len(relevant_pairs)} relevant historical Q&A pairs.")
        return formatted_context

    except Exception as e:
        log("context", f"⚠️ Error fetching historical context: {e}")
        return ""


async def main():
    """
    The main entry point for the AI agent.

    This function initializes the agent, including its configuration and tool servers.
    It then enters a loop to process user input, applying heuristics, running the
    perception-decision-action cycle, and displaying the final answer.
    """
    global mcp_dispatcher
    log("init", "Starting Cortex-R agent...")

    # --- Load Configuration ---
    with open("config/profiles.yaml", "r") as f:
        config = yaml.safe_load(f)

    mcp_server_configs = config.get("mcp_servers", [])
    if not mcp_server_configs:
        log("init", "❌ No MCP servers configured. Exiting.")
        return

    # --- Initialize Tool Servers ---
    log("init", "Initializing tool servers...")
    mcp_dispatcher = MultiMCP(server_configs=mcp_server_configs)
    await mcp_dispatcher.initialize()
    log("init", "✅ Tool servers initialized.")

    # --- Main Loop ---
    while True:
        try:
            user_input = input(" CORTEX-R > ")
            if user_input.lower() in ["exit", "quit"]:
                break

            # 1. Apply heuristic rules to user input
            allowed, sanitized_input, rejection_message = apply_input_heuristics(user_input)
            if not allowed:
                print(f"⚠️ {rejection_message}")
                continue

            if sanitized_input != user_input:
                log("heuristic", f"Input modified: '{sanitized_input}'")

            # 2. (Optional) Get selective context from memory
            injected_context = await get_selectively_injected_context(sanitized_input)
            if injected_context:
                final_input = f"{injected_context}\nUser task: {sanitized_input}"
            else:
                final_input = sanitized_input

            # 3. Create Agent Context for this session
            # We pass full server descriptions for the perception phase
            server_descriptions = [
                {"id": cfg["id"], "description": cfg["description"]}
                for cfg in mcp_server_configs
            ]

            context = AgentContext(
                user_input=final_input,
                dispatcher=mcp_dispatcher,
                mcp_server_descriptions=server_descriptions
            )

            # 4. Run the agent loop
            agent_loop = AgentLoop(context)
            result = await agent_loop.run()

            # 5. Display the final answer
            final_answer = result.get("result", "No final answer found.")
            if final_answer.startswith("FINAL_ANSWER:"):
                final_answer = final_answer.split("FINAL_ANSWER:", 1)[1].strip()

            print(f"\n💡 Final Answer: {final_answer}\n")

        except KeyboardInterrupt:
            break

    log("shutdown", "Agent shutting down...")
    if mcp_dispatcher:
        await mcp_dispatcher.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
