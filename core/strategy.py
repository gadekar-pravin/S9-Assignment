# modules/strategy.py

from typing import List, Optional, Any
from modules.perception import PerceptionResult
from modules.memory import MemoryItem
from modules.model_manager import ModelManager
from core.context import AgentContext
from modules.tools import filter_tools_by_hint, summarize_tools, load_prompt

# Optional fallback logger
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

def select_decision_prompt_path(planning_mode: str, exploration_mode: Optional[str] = None) -> str:
    """
    Selects the appropriate decision prompt file based on the planning strategy.

    Args:
        planning_mode (str): The primary planning mode ('conservative' or 'exploratory').
        exploration_mode (Optional[str]): The exploration sub-mode ('parallel' or 'sequential').

    Returns:
        str: The file path to the selected prompt template.
    """
    if planning_mode == "conservative":
        return "prompts/decision_prompt_conservative.txt"
    elif planning_mode == "exploratory":
        if exploration_mode == "parallel":
            return "prompts/decision_prompt_exploratory_parallel.txt"
        elif exploration_mode == "sequential":
            return "prompts/decision_prompt_exploratory_sequential.txt"
    return "prompts/decision_prompt_conservative.txt"  # safe fallback

model = ModelManager()

async def decide_next_action(
    context: AgentContext,
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    all_tools: List[Any],
    last_result: str = "",
    failed_tools: List[str] = [],
    force_replan: bool = False,
) -> str:
    """
    Determines the next action or plan based on the current context and strategy.

    This function serves as the main entry point for the decision-making process,
    routing to different planning strategies like 'conservative' or 'exploratory'.

    Args:
        context (AgentContext): The current session's context.
        perception (PerceptionResult): The output from the perception phase.
        memory_items (List[MemoryItem]): A list of items from the session's memory.
        all_tools (List[Any]): A list of all available tools.
        last_result (str): The result from the previous action (currently unused).
        failed_tools (List[str]): A list of tools that have failed in the current step.
        force_replan (bool): A flag to force replanning, ignoring previous suggestions.

    Returns:
        str: A string representing the generated plan (e.g., a Python `solve()` function).
    """

    strategy = context.agent_profile.strategy
    planning_mode = strategy.planning_mode
    exploration_mode = strategy.exploration_mode
    memory_fallback_enabled = strategy.memory_fallback_enabled
    max_steps = strategy.max_steps
    step_num = context.step + 1

    # === Select correct decision prompt path ===
    prompt_path = select_decision_prompt_path(planning_mode, exploration_mode)

    # Filter tools based on Perception hint
    tool_hint = perception.tool_hint
    filtered_tools = filter_tools_by_hint(all_tools, hint=tool_hint)
    filtered_summary = summarize_tools(filtered_tools)

    if planning_mode == "conservative":
        return await conservative_plan(
            perception, memory_items, filtered_summary, all_tools, step_num, max_steps,
            prompt_path, force_replan
        )

    if planning_mode == "exploratory":
        return await exploratory_plan(
            perception, memory_items, filtered_summary, all_tools, step_num, max_steps,
            exploration_mode, memory_fallback_enabled, prompt_path, force_replan, failed_tools
        )

    # Fallback
    full_summary = summarize_tools(all_tools)
    plan = await generate_plan(
        perception=perception,
        memory_items=memory_items,
        tool_descriptions=full_summary,
        prompt_path=prompt_path,
        step_num=step_num,
        max_steps=max_steps,
    )
    return plan

# === CONSERVATIVE MODE ===
async def conservative_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    filtered_summary: str,
    all_tools: List[Any],
    step_num: int,
    max_steps: int,
    prompt_path: str,
    force_replan: bool
) -> str:
    """
    Generates a plan using a conservative strategy, typically focusing on a single tool call.

    Args:
        perception (PerceptionResult): The output from the perception phase.
        memory_items (List[MemoryItem]): A list of items from the session's memory.
        filtered_summary (str): A summary of tools filtered by the perception hint.
        all_tools (List[Any]): A list of all available tools, for fallback.
        step_num (int): The current step number.
        max_steps (int): The maximum number of steps.
        prompt_path (str): The path to the prompt template for planning.
        force_replan (bool): A flag to force replanning with all tools.

    Returns:
        str: The generated plan.
    """

    if force_replan or not filtered_summary.strip():
        log("strategy", "⚠️ Force replan or no filtered tools. Using all tools.")
        tool_context = summarize_tools(all_tools)
    else:
        tool_context = filtered_summary

    plan = await generate_plan(
        perception=perception,
        memory_items=memory_items,
        tool_descriptions=tool_context,
        prompt_path=prompt_path,
        step_num=step_num,
        max_steps=max_steps
    )

    return plan

# === EXPLORATORY MODE ===
async def exploratory_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    filtered_summary: str,
    all_tools: List[Any],
    step_num: int,
    max_steps: int,
    exploration_mode: str,
    memory_fallback_enabled: bool,
    prompt_path: str,
    force_replan: bool,
    failed_tools: List[str]
) -> str:
    """
    Generates a plan using an exploratory strategy, potentially considering multiple options.

    Args:
        perception (PerceptionResult): The output from the perception phase.
        memory_items (List[MemoryItem]): A list of items from the session's memory.
        filtered_summary (str): A summary of tools filtered by the perception hint.
        all_tools (List[Any]): A list of all available tools.
        step_num (int): The current step number.
        max_steps (int): The maximum number of steps.
        exploration_mode (str): The specific exploration mode ('parallel' or 'sequential').
        memory_fallback_enabled (bool): Whether to use memory fallback if stuck.
        prompt_path (str): The path to the prompt template.
        force_replan (bool): A flag to force replanning.
        failed_tools (List[str]): A list of tools that have already failed.

    Returns:
        str: The generated plan.
    """

    if force_replan:
        log("strategy", "⚠️ Force replan triggered. Attempting fallback.")

        if memory_fallback_enabled:
            fallback_tools = find_recent_successful_tools(memory_items)
            if fallback_tools:
                log("strategy", f"✅ Memory fallback tools found: {fallback_tools}")
                fallback_summary = summarize_tools(fallback_tools)
                return await generate_plan(
                    perception=perception,
                    memory_items=memory_items,
                    tool_descriptions=fallback_summary,
                    prompt_path=prompt_path,
                    step_num=step_num,
                    max_steps=max_steps
                )
            else:
                log("strategy", "⚠️ No memory fallback tools. Using all tools.")

        tool_context = summarize_tools(all_tools)
        return await generate_plan(
            perception=perception,
            memory_items=memory_items,
            tool_descriptions=tool_context,
            prompt_path=prompt_path,
            step_num=step_num,
            max_steps=max_steps
        )

    if not filtered_summary.strip():
        log("strategy", "⚠️ No filtered tools. Using all tools.")
        tool_context = summarize_tools(all_tools)
    else:
        tool_context = filtered_summary

    plan = await generate_plan(
        perception=perception,
        memory_items=memory_items,
        tool_descriptions=tool_context,
        prompt_path=prompt_path,
        step_num=step_num,
        max_steps=max_steps
    )

    return plan

# === GENERATE PLAN ===
async def generate_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: str,
    prompt_path: str,
    step_num: int,
    max_steps: int,
) -> str:
    """
    Asks the language model to generate a `solve()` function based on the provided context.

    Args:
        perception (PerceptionResult): The output from the perception phase.
        memory_items (List[MemoryItem]): A list of items from the session's memory.
        tool_descriptions (str): A summary of the available tools.
        prompt_path (str): The path to the prompt template.
        step_num (int): The current step number.
        max_steps (int): The maximum number of steps.

    Returns:
        str: The raw string of the generated `solve()` function.
    """

    prompt_template = load_prompt(prompt_path)

    final_prompt = prompt_template.format(
        tool_descriptions=tool_descriptions,
        user_input=perception.user_input
    )

    raw = (await model.generate_text(final_prompt)).strip()
    log("plan", f"Generated solve():\n{raw}")

    return raw

# === MEMORY FALLBACK LOGIC ===
def find_recent_successful_tools(memory_items: List[MemoryItem], limit: int = 5) -> List[str]:
    """
    Finds the names of recently used, successful tools from memory.

    Args:
        memory_items (List[MemoryItem]): A list of items from the session's memory.
        limit (int): The maximum number of unique tool names to return.

    Returns:
        List[str]: A list of unique tool names that were recently successful.
    """
    successful_tools = []

    for item in reversed(memory_items):
        if item.type == "tool_output" and item.success and item.tool_name:
            if item.tool_name not in successful_tools:
                successful_tools.append(item.tool_name)
        if len(successful_tools) >= limit:
            break

    return successful_tools
