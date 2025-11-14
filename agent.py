# agent.py

import asyncio
import yaml
from core.loop import AgentLoop
from core.session import MultiMCP
from core.context import MemoryItem, AgentContext
import datetime
from pathlib import Path
import json
import warnings
from heuristic_rules import apply_input_heuristics

# Quiet noisy SWIG-related DeprecationWarnings emitted by third-party deps.
warnings.filterwarnings(
    "ignore",
    message=r"builtin type (?:SwigPyPacked|SwigPyObject|swigvarlink) has no __module__ attribute",
    category=DeprecationWarning,
)


def log(stage: str, msg: str):
    """Simple timestamped console logger."""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage}] {msg}")


async def main():
    print("🧠 Cortex-R Agent Ready")
    current_session = None

    with open("config/profiles.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers_list = profile.get("mcp_servers", [])
        mcp_servers = {server["id"]: server for server in mcp_servers_list}

    multi_mcp = MultiMCP(server_configs=list(mcp_servers.values()))
    await multi_mcp.initialize()

    # --- This is the new "best of both worlds" injection logic ---
    async def get_selectively_injected_context(user_query: str, dispatcher: MultiMCP) -> str:
        """
        Calls the memory server to find relevant history.
        If found, formats it and prepends it to the user's query.
        """
        # Define a relevance threshold (lower L2 distance is better)
        RELEVANCE_THRESHOLD = 300.0  # Adjust this based on your embedding model

        try:
            log("memory-inject", f"Searching history for query: {user_query}")
            hist_raw = await dispatcher.call_tool(
                "search_historical_conversations",
                {"input": {"query": user_query, "max_results": 2}}
            )

            hist_json = json.loads(hist_raw.content[0].text)
            matches = hist_json.get("result", {}).get("matches", [])

            if not matches:
                log("memory-inject", "No relevant history found.")
                return user_query  # Return original query

            # Filter matches by the relevance threshold
            relevant_matches = [m for m in matches if m.get("l2_distance", 1000) < RELEVANCE_THRESHOLD]

            if not relevant_matches:
                log("memory-inject", f"Matches found, but none below threshold {RELEVANCE_THRESHOLD}.")
                return user_query  # Return original query

            # Format the relevant history
            historical_block = []
            for conv in relevant_matches:
                dt = datetime.datetime.fromtimestamp(conv['timestamp']).strftime('%Y-%m-%d')
                historical_block.append(
                    f"On {dt}, you had this exchange:\n"
                    f"User: {conv['user_query']}\n"
                    f"Agent: {conv['final_answer']}"
                )

            historical_summary = "\n\n---\n\n".join(historical_block)
            log("memory-inject", "Injecting relevant historical context.")

            # Return the new, combined prompt
            return (
                f"User's current query: {user_query}\n\n"
                f"For your reference, here is some highly relevant context from your past conversations. "
                f"Use this to inform your answer:\n\n"
                f"{historical_summary}"
            )

        except Exception as e:
            log("memory-inject", f"Could not fetch historical context: {e}")
            return user_query  # Fail safe: return original query

    try:
        while True:
            user_input = input("🧑 What do you want to solve today? → ")
            if user_input.lower() == 'exit':
                break
            if user_input.lower() == 'new':
                current_session = None
                log("agent", "Starting a new session.")
                continue

            allowed, sanitized_input, blocked_msg = apply_input_heuristics(user_input)
            if not allowed:
                log("agent", "Blocked or unprocessable input.")
                print(f"⚠️ {blocked_msg}")
                continue
            if sanitized_input != user_input:
                log("agent", "Sanitized user input via heuristics.")
            user_input = sanitized_input

            # === 🧠 AUTOMATIC HISTORICAL CONTEXT INJECTION ===
            # This is the "Selective Injection" step.
            injected_user_input = await get_selectively_injected_context(user_input, multi_mcp)
            # =================================================

            while True:
                context = AgentContext(
                    user_input=injected_user_input,  # Use the new, context-aware input
                    session_id=current_session,
                    dispatcher=multi_mcp,
                    mcp_server_descriptions=mcp_servers,
                )
                agent = AgentLoop(context)
                if not current_session:
                    current_session = context.session_id

                result = await agent.run()

                if isinstance(result, dict):
                    answer = result["result"]
                    if "FINAL_ANSWER:" in answer:
                        print(f"\n💡 Final Answer: {answer.split('FINAL_ANSWER:')[1].strip()}")
                        break
                    elif "FURTHER_PROCESSING_REQUIRED:" in answer:
                        user_input = answer.split("FURTHER_PROCESSING_REQUIRED:")[1].strip()
                        log("agent", "Further processing required. Re-running loop...")

                        # --- Re-inject context for the follow-up step ---
                        injected_user_input = await get_selectively_injected_context(user_input, multi_mcp)
                        continue  # Re-run agent with updated input
                    else:
                        print(f"\n💡 Final Answer (raw): {answer}")
                        break
                else:
                    print(f"\n💡 Final Answer (unexpected): {result}")
                    break
    except KeyboardInterrupt:
        print("\n👋 Received exit signal. Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())



# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?
# which course are we teaching on Canvas LMS? "H:\DownloadsH\How to use Canvas LMS.pdf"
# Summarize this page: https://theschoolof.ai/
# Summarize this page: https://www.google.com/
# What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge?
# Who won the Bihar 2025 assembly election?
# What is the factorial of 3?
# What is the cube root of 27?
