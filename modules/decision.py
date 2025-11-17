from typing import List, Optional
from modules.perception import PerceptionResult
from modules.memory import MemoryItem
from modules.model_manager import ModelManager
from modules.tools import load_prompt
import re

# Optional logging fallback
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

model = ModelManager()


# prompt_path = "prompts/decision_prompt.txt"

async def generate_plan(
    user_input: str,
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: Optional[str],
    prompt_path: str,
    step_num: int = 1,
    max_steps: int = 3,
) -> str:

    """
    Generates a Python `solve()` function using a language model.

    This function constructs a prompt from the user input, perception results,
    memory, and available tools, then calls the language model to generate a
    plan in the form of a Python function.

    Args:
        user_input (str): The original user input.
        perception (PerceptionResult): The output from the perception phase.
        memory_items (List[MemoryItem]): A list of memory items from the current session.
        tool_descriptions (str): A description of the available tools.
        prompt_path (str): The file path to the prompt template.
        step_num (int): The current step number in the agent's loop.
        max_steps (int): The total number of steps the agent is allowed to take.

    Returns:
        str: The generated Python code for the `solve()` function, or a
             fallback "FINAL_ANSWER" if generation fails.
    """

    memory_texts = "\n".join(f"- {m.text}" for m in memory_items) or "None"

    prompt_template = load_prompt(prompt_path)

    prompt = prompt_template
    replacements = {
        "{tool_descriptions}": tool_descriptions or "None",
        "{user_input}": user_input or "",
        "{memory_texts}": memory_texts,
        "{step_num}": str(step_num),
        "{max_steps}": str(max_steps),
    }

    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, str(value))

    prompt = prompt.replace("{{", "{").replace("}}", "}")


    try:
        raw = (await model.generate_text(prompt)).strip()
        log("plan", f"LLM output: {raw}")

        # If fenced in ```python ... ```, extract
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("python"):
                raw = raw[len("python"):].strip()

        if re.search(r"^\s*(async\s+)?def\s+solve\s*\(", raw, re.MULTILINE):
            return raw  # ✅ Correct, it's a full function
        else:
            log("plan", "⚠️ LLM did not return a valid solve(). Defaulting to FINAL_ANSWER")
            return "FINAL_ANSWER: [Could not generate valid solve()]"


    except Exception as e:
        log("plan", f"⚠️ Planning failed: {e}")
        return "FINAL_ANSWER: [unknown]"
