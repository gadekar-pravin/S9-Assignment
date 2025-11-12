# Cortex-R AI Agent - Developer Guide for Beginners

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Key Concepts](#architecture--key-concepts)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Agent](#running-the-agent)
7. [Project Structure](#project-structure)
8. [Key Modules Explained](#key-modules-explained)
9. [How the Agent Works](#how-the-agent-works)
10. [Testing the Agent](#testing-the-agent)
11. [Troubleshooting](#troubleshooting)
12. [Common Errors & Solutions](#common-errors--solutions)

---

## Project Overview

**Cortex-R** is an intelligent AI reasoning agent that can solve complex tasks by breaking them down into smaller steps and using specialized tools. Think of it as an AI assistant that can:

- Perform mathematical calculations (addition, multiplication, trigonometry, etc.)
- Search and extract information from documents (PDFs, web pages)
- Search the internet for real-time information
- Execute Python code in a sandbox environment
- Remember previous conversations and learn from them

### What Makes It Special?

- **Perception-Decision-Action Loop**: The agent observes your request, decides which tools to use, and executes actions
- **Multi-Tool Support**: Uses MCP (Model Context Protocol) servers to access various tools
- **Memory System**: Remembers past interactions across sessions
- **Flexible Planning**: Can work in conservative (one step at a time) or exploratory (try multiple approaches) mode

---

## Architecture & Key Concepts

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                     User Input                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  1. PERCEPTION: Understands intent & selects servers    │
│     - What is the user asking?                          │
│     - Which tools are needed?                           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  2. DECISION: Creates execution plan                    │
│     - Generates a Python solve() function               │
│     - Chains multiple tool calls if needed              │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  3. ACTION: Executes the plan in sandbox                │
│     - Runs the solve() function                         │
│     - Calls MCP tools                                   │
│     - Returns FINAL_ANSWER or asks for more processing  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Memory & User Response                     │
└─────────────────────────────────────────────────────────┘
```

### MCP (Model Context Protocol)

MCP is a protocol that allows the agent to communicate with external tools. Each MCP server provides a set of tools:

- **mcp_server_1.py**: Math operations, image processing, Python sandbox
- **mcp_server_2.py**: Document search, PDF extraction, webpage conversion
- **mcp_server_3.py**: Web search, HTML downloading

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

### Required Software

1. **Python 3.11 or higher**
   - Check your version: `python --version`
   - Download from: https://www.python.org/downloads/

2. **uv Package Manager** (recommended) or pip
   - Install uv: `pip install uv`
   - Alternative: Use `pip` directly

3. **Git** (optional, for version control)
   - Download from: https://git-scm.com/downloads

### Required API Keys

You'll need to obtain the following API keys:

1. **Google Gemini API Key** (for the default LLM)
   - Get it from: https://ai.google.dev/
   - Free tier available for development

2. **Optional: Ollama** (for local LLM models)
   - Install from: https://ollama.ai/
   - Allows running models like phi4, gemma3, qwen2.5 locally

### System Requirements

- **OS**: Windows, macOS, or Linux
- **RAM**: Minimum 4GB (8GB+ recommended)
- **Storage**: At least 500MB free space
- **Internet**: Required for API calls and web searches

---

## Installation

Follow these steps carefully to set up the project:

### Step 1: Clone or Download the Project

If you have the project folder already, skip this step. Otherwise:

```bash
cd /path/to/your/projects
# If using git:
git clone <repository-url>
cd "S9 Share"
```

### Step 2: Install Dependencies

The project uses `pyproject.toml` and `uv.lock` for dependency management.

**Option A: Using uv (Recommended)**

```bash
# Install uv if you haven't already
pip install uv

# Install all dependencies
uv sync
```

**Option B: Using pip**

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install asyncio bs4 python-dotenv faiss-cpu httpx llama-index \
    llama-index-embeddings-google-genai markitdown mcp pillow \
    pydantic pymupdf4llm requests rich tqdm trafilatura
```

### Step 3: Set Up Environment Variables

Create a `.env` file in the project root directory:

```bash
# Create the file
touch .env  # On macOS/Linux
# or
type nul > .env  # On Windows
```

Add your API keys to the `.env` file:

```env
# Google Gemini API Key (required)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Add other API keys as needed
```

**Important**: Never commit your `.env` file to version control! It contains sensitive information.

### Step 4: Update Configuration Paths

The `config/profiles.yaml` file contains hardcoded paths that need to be updated to match your system.

Open `config/profiles.yaml` and update the `cwd` (current working directory) paths:

```yaml
mcp_servers:
  - id: math
    script: mcp_server_1.py
    cwd: /Users/pravingadekar/Documents/EAG2/S9 Share  # ← Change this to your actual path
    # ... rest of config

  - id: documents
    script: mcp_server_2.py
    cwd: /Users/pravingadekar/Documents/EAG2/S9 Share  # ← Change this to your actual path
    # ... rest of config

  - id: websearch
    script: mcp_server_3.py
    cwd: /Users/pravingadekar/Documents/EAG2/S9 Share  # ← Change this to your actual path
    # ... rest of config
```

**How to find your actual path:**

```bash
# On macOS/Linux:
pwd

# On Windows:
cd
```

Copy the output and replace the `cwd` values in `profiles.yaml`.

### Step 5: Verify Installation

Test that all dependencies are installed correctly:

```bash
python -c "import asyncio, faiss, httpx, mcp; print('All dependencies installed successfully!')"
```

If you see the success message, you're ready to go!

---

## Configuration

The agent uses two main configuration files:

### 1. `config/models.json`

Defines which LLM models to use for text generation and embeddings.

```json
{
  "defaults": {
    "text_generation": "gemini",  // Which model to use by default
    "embedding": "nomic"           // Which embedding model to use
  },
  "models": {
    "gemini": {
      "type": "gemini",
      "model": "gemini-2.0-flash",
      "embedding_model": "models/embedding-001",
      "api_key_env": "GEMINI_API_KEY"  // Reads from .env file
    },
    // Other models (ollama) can be configured here
  }
}
```

**To change the default model**, edit the `defaults.text_generation` value to one of the model keys (e.g., "phi4", "gemma3:12b").

### 2. `config/profiles.yaml`

Configures the agent's behavior and strategy.

```yaml
agent:
  name: Cortex-R
  id: cortex_r_002
  description: A reasoning-driven AI agent

strategy:
  planning_mode: conservative   # Options: conservative, exploratory
  exploration_mode: parallel    # Options: parallel, sequential
  max_steps: 3                  # Maximum reasoning steps per query
  max_lifelines_per_step: 3     # Retry attempts per step

memory:
  memory_service: true          # Enable memory system
  summarize_tool_results: true  # Store summarized results
  tag_interactions: true        # Tag interactions for search

llm:
  text_generation: gemini       # LLM model to use
  embedding: nomic              # Embedding model for document search

mcp_servers:
  # List of MCP servers and their capabilities
  # (Update paths as mentioned in installation)
```

**Key Configuration Options:**

- **planning_mode**:
  - `conservative`: One tool call at a time (safer, slower)
  - `exploratory`: Multiple approaches in parallel (faster, more creative)

- **max_steps**: How many reasoning iterations before giving up (increase for complex tasks)

- **max_lifelines_per_step**: Retry attempts if a step fails

---

## Running the Agent

### Starting the Agent

```bash
python agent.py
```

You should see:

```
🧠 Cortex-R Agent Ready
🧑 What do you want to solve today? →
```

### Example Interactions

#### Example 1: Simple Math

```
🧑 What do you want to solve today? → What is 15 + 27?

[Processing...]

💡 Final Answer: 42
```

#### Example 2: Web Search

```
🧑 What do you want to solve today? → What is the capital of France?

[Processing...]

💡 Final Answer: The capital of France is Paris.
```

#### Example 3: Document Search

```
🧑 What do you want to solve today? → Search my documents for information about Canvas LMS

[Processing...]

💡 Final Answer: [Information extracted from documents/How to use Canvas LMS.pdf]
```

### Special Commands

- **`exit`**: Quit the agent
- **`new`**: Start a new session (clears current conversation history)

### Understanding the Output

While processing, you'll see:

```
🔁 Step 1/3 starting...
[perception] {...}           # What the agent understood
[plan] {...}                 # The execution plan it created
[action] {...}               # Tool execution results
```

This helps you debug and understand what the agent is doing.

---

## Project Structure

```
S9 Share/
├── agent.py                     # Main entry point - START HERE
├── models.py                    # Pydantic models for all tools
├── pyproject.toml               # Project dependencies
├── uv.lock                      # Locked dependency versions
│
├── config/                      # Configuration files
│   ├── models.json              # LLM model configurations
│   └── profiles.yaml            # Agent behavior settings
│
├── core/                        # Core system components
│   ├── context.py               # AgentContext (session state)
│   ├── loop.py                  # Main agent loop (Perception→Decision→Action)
│   ├── session.py               # MCP client management (MultiMCP)
│   └── strategy.py              # Strategy selection logic
│
├── modules/                     # Agent modules
│   ├── perception.py            # Intent recognition & server selection
│   ├── decision.py              # Plan generation (creates solve() function)
│   ├── action.py                # Python sandbox execution
│   ├── memory.py                # Session memory management
│   ├── model_manager.py         # LLM client wrapper (Gemini/Ollama)
│   ├── tools.py                 # Utility functions
│   └── mcp_server_memory.py     # Memory tools for MCP
│
├── prompts/                     # LLM prompt templates
│   ├── perception_prompt.txt    # For intent understanding
│   ├── decision_prompt.txt      # For plan generation
│   └── decision_prompt_*.txt    # Strategy-specific prompts
│
├── mcp_server_1.py              # Math & Python sandbox tools
├── mcp_server_2.py              # Document & PDF extraction tools
├── mcp_server_3.py              # Web search tools
│
├── documents/                   # Sample documents for testing
│   ├── How to use Canvas LMS.pdf
│   ├── dlf.md
│   └── ...
│
├── faiss_index/                 # Document search index
│   ├── index.bin                # FAISS vector index
│   └── metadata.json            # Document metadata
│
└── memory/                      # Conversation history (auto-created)
    └── [YYYY]/[MM]/[DD]/        # Organized by date
        └── session-*.json       # Individual session files
```

---

## Key Modules Explained

### 1. `agent.py` - Main Entry Point

This is where everything starts. It:
1. Loads configuration from `config/profiles.yaml`
2. Initializes all MCP servers
3. Starts the interactive loop
4. Handles user input and session management

**Key Function:**
```python
async def main():
    # Initialize MCP servers
    multi_mcp = MultiMCP(server_configs=list(mcp_servers.values()))
    await multi_mcp.initialize()

    # Main conversation loop
    while True:
        user_input = input("🧑 What do you want to solve today? → ")
        # ... process with AgentLoop
```

### 2. `core/loop.py` - Agent Loop

Implements the Perception → Decision → Action cycle.

**Key Class:**
```python
class AgentLoop:
    async def run(self):
        for step in range(max_steps):
            # 1. Perception: Understand the query
            perception = await run_perception(context, user_input)

            # 2. Decision: Generate plan
            plan = await generate_plan(...)

            # 3. Action: Execute plan
            result = await run_python_sandbox(plan, dispatcher)

            if "FINAL_ANSWER:" in result:
                return result  # Done!
            # Otherwise, continue to next step
```

### 3. `modules/perception.py` - Intent Recognition

Analyzes user input and selects which MCP servers are needed.

**Example:**
- User: "What is 5 + 3?"
- Perception: Intent=math, Selected Servers=["math"]
- User: "Search the web for Python tutorials"
- Perception: Intent=search, Selected Servers=["websearch"]

### 4. `modules/decision.py` - Plan Generation

Uses an LLM to generate a Python `solve()` function that chains tool calls.

**Example Output:**
```python
async def solve():
    # FUNCTION_CALL: 1
    """Add two numbers. Usage: input={"a": 1, "b": 2}"""
    input = {"a": 5, "b": 3}
    result = await mcp.call_tool('add', input)

    return f"FINAL_ANSWER: {result}"
```

### 5. `modules/action.py` - Sandbox Execution

Safely executes the generated `solve()` function in a sandboxed Python environment.

**Safety Features:**
- Limited imports (only `json`, `re` allowed)
- Max 5 tool calls per plan
- Isolated namespace (can't access system resources)

### 6. `modules/memory.py` - Session Memory

Stores conversation history and tool results for each session.

**Memory Structure:**
```json
{
  "timestamp": 1234567890,
  "type": "tool_output",
  "tool_name": "add",
  "tool_args": {"a": 5, "b": 3},
  "tool_result": {"result": 8},
  "success": true,
  "tags": ["math"]
}
```

### 7. `core/session.py` - MCP Client

Manages connections to MCP servers and routes tool calls.

**Key Class:**
```python
class MultiMCP:
    async def initialize(self):
        # Discover tools from all MCP servers

    async def call_tool(self, tool_name: str, arguments: dict):
        # Route call to the correct MCP server
```

### 8. `modules/model_manager.py` - LLM Client

Abstracts LLM calls to support multiple providers (Gemini, Ollama).

**Example Usage:**
```python
model = ModelManager()
response = await model.generate_text("What is 2+2?")
```

---

## How the Agent Works

Let's walk through a complete example to understand the flow.

### User Query: "What is the ASCII sum of INDIA?"

#### Step 1: Perception (modules/perception.py)

The agent analyzes the query:
```json
{
  "intent": "Convert string to ASCII values and sum them",
  "entities": ["INDIA"],
  "tool_hint": "strings_to_chars_to_int, add",
  "selected_servers": ["math"]
}
```

#### Step 2: Decision (modules/decision.py)

The agent generates a plan using the LLM:

```python
async def solve():
    # FUNCTION_CALL: 1
    """Convert string to ASCII integers."""
    input = {"string": "INDIA"}
    result = await mcp.call_tool('strings_to_chars_to_int', input)
    # result = [73, 78, 68, 73, 65]

    # FUNCTION_CALL: 2
    """Sum a list of numbers."""
    input = {"numbers": result}
    result = await mcp.call_tool('sum_list', input)

    return f"FINAL_ANSWER: The ASCII sum of INDIA is {result}"
```

#### Step 3: Action (modules/action.py)

The sandbox executes the plan:
1. Calls `strings_to_chars_to_int` with `{"string": "INDIA"}`
2. Gets result: `[73, 78, 68, 73, 65]`
3. Calls `sum_list` with `{"numbers": [73, 78, 68, 73, 65]}`
4. Gets result: `357`
5. Returns: `"FINAL_ANSWER: The ASCII sum of INDIA is 357"`

#### Step 4: Memory Update (modules/memory.py)

The interaction is stored in memory for future reference:
- Tool calls made
- Results received
- Success/failure status
- Session metadata

---

## Testing the Agent

### Test Cases

Here are some queries you can try to test different capabilities:

#### Math Operations
```
What is 15 + 27?
Calculate 5 to the power of 3
What is the square root of 144?
Find the factorial of 5
```

#### String Processing
```
What are the ASCII values of HELLO?
Find the ASCII sum of PYTHON
```

#### Document Search
```
Search my documents for information about Canvas LMS
What information is in the DLF document?
Extract text from the Tesla document
```

#### Web Search
```
What is the current population of Tokyo?
Search for the latest Python features
Find information about quantum computing
```

#### Complex Queries (Multi-step)
```
Find the ASCII values of INDIA and return the sum of their exponentials
Search the web for the Eiffel Tower height and convert it to meters
```

### Expected Behavior

#### Success Case
```
🔁 Step 1/3 starting...
[perception] {"intent": "arithmetic", "selected_servers": ["math"]}
[plan] async def solve(): ...
💡 Final Answer: 42
```

#### Retry Case (Tool failure)
```
🔁 Step 1/3 starting...
[perception] {...}
[plan] {...}
⚠️ Execution failed
🛠 Retrying... Lifelines left: 2
```

#### Max Steps Reached
```
🔁 Step 3/3 starting...
[perception] {...}
[plan] {...}
⚠️ Max steps reached without finding final answer.
💡 Final Answer: [Max steps reached]
```

---

## Troubleshooting

### Issue 1: "No module named 'mcp'"

**Cause**: Dependencies not installed correctly.

**Solution**:
```bash
pip install mcp
# or
uv sync
```

### Issue 2: "GEMINI_API_KEY not found"

**Cause**: Missing or incorrect `.env` file.

**Solution**:
1. Create `.env` in project root
2. Add: `GEMINI_API_KEY=your_actual_key_here`
3. Restart the agent

### Issue 3: "FileNotFoundError: config/profiles.yaml"

**Cause**: Running agent from wrong directory.

**Solution**:
```bash
cd /path/to/S9\ Share
python agent.py
```

### Issue 4: MCP servers not initializing

**Cause**: Incorrect `cwd` paths in `config/profiles.yaml`.

**Solution**:
1. Find your actual path: `pwd` (macOS/Linux) or `cd` (Windows)
2. Update all `cwd` values in `config/profiles.yaml`
3. Restart the agent

### Issue 5: "Tool 'X' not found on any server"

**Cause**: MCP server script not running or tool not registered.

**Solution**:
1. Check that `mcp_server_1.py`, `mcp_server_2.py`, `mcp_server_3.py` exist
2. Verify paths in `config/profiles.yaml`
3. Check MCP server logs during initialization

### Issue 6: "Max tool calls exceeded"

**Cause**: Plan tries to call more than 5 tools.

**Solution**: This is a safety limit. The agent should generate a simpler plan. If this happens frequently:
1. Increase `MAX_TOOL_CALLS_PER_PLAN` in `modules/action.py`
2. Or break your query into smaller parts

### Issue 7: Slow response times

**Cause**: Using remote API (Gemini) or large models.

**Solutions**:
- Use a faster model: Change `text_generation` in `config/profiles.yaml` to `"gemini"` (already default)
- Or install Ollama and use local models (faster, no API calls)

### Issue 8: "Could not generate valid solve()"

**Cause**: LLM failed to generate proper Python code.

**Solution**:
1. The agent will retry automatically (up to `max_lifelines_per_step` times)
2. If it persists, try rephrasing your query more clearly
3. Check that selected tools can actually solve the task

---

## Common Errors & Solutions

### Import Errors

```
ImportError: cannot import name 'X' from 'Y'
```

**Solution**: Reinstall dependencies
```bash
pip install --upgrade --force-reinstall -r requirements.txt
# or
uv sync --refresh
```

### API Errors

```
google.api_core.exceptions.PermissionDenied: API key not valid
```

**Solution**:
1. Get a valid Gemini API key from https://ai.google.dev/
2. Update `.env` file
3. Ensure no extra spaces: `GEMINI_API_KEY=abc123xyz` (not `= abc123xyz`)

### JSON Parsing Errors

```
json.decoder.JSONDecodeError: Expecting value
```

**Solution**: This usually means the LLM returned malformed output. The agent should retry automatically. If it persists:
1. Check `prompts/perception_prompt.txt` and `prompts/decision_prompt.txt` are not corrupted
2. Try a different model in `config/models.json`

### Memory Errors

```
PermissionError: [Errno 13] Permission denied: 'memory/...'
```

**Solution**:
```bash
# On macOS/Linux:
chmod -R 755 memory/

# On Windows: Right-click folder → Properties → Security → Give Full Control
```

### Path Errors (Windows)

```
FileNotFoundError: [WinError 3] The system cannot find the path specified
```

**Solution**: Use forward slashes or raw strings:
```python
# Wrong:
cwd: "C:\Users\Name\Project"

# Right:
cwd: "C:/Users/Name/Project"
# or
cwd: "C:\\Users\\Name\\Project"
```

---

## Additional Resources

### Learning More

1. **MCP Protocol**: https://github.com/anthropics/mcp
2. **Gemini API**: https://ai.google.dev/docs
3. **FAISS (Document Search)**: https://github.com/facebookresearch/faiss
4. **Pydantic (Data Validation)**: https://docs.pydantic.dev/

### Extending the Agent

#### Adding a New Tool

1. Define input/output models in `models.py`:
```python
class MyToolInput(BaseModel):
    param: str

class MyToolOutput(BaseModel):
    result: str
```

2. Add tool to an MCP server (e.g., `mcp_server_1.py`):
```python
@mcp.tool()
def my_tool(input: MyToolInput) -> MyToolOutput:
    """Description of what this tool does."""
    result = input.param.upper()  # Your logic here
    return MyToolOutput(result=result)
```

3. Update `config/profiles.yaml` to include the new tool in capabilities

4. Restart the agent

#### Changing Agent Behavior

Edit `config/profiles.yaml`:
- Make it more exploratory: `planning_mode: exploratory`
- Increase reasoning depth: `max_steps: 5`
- Allow more retries: `max_lifelines_per_step: 5`

### Tips for Juniors

1. **Start Simple**: Test with basic math queries first
2. **Read the Logs**: The `[perception]`, `[plan]`, and `[action]` logs tell you exactly what's happening
3. **Check Memory**: Look at `memory/` folder to see what the agent remembers
4. **Experiment**: Try different queries and see how the agent responds
5. **Use Exploratory Mode**: Set `planning_mode: exploratory` to see how the agent tries multiple approaches

---

## FAQ

**Q: Can I use this without internet?**
A: Partially. You need internet for Gemini API calls, but you can use Ollama with local models for offline operation.

**Q: How do I add my own documents?**
A: Place PDF files in the `documents/` folder. The agent will index them automatically when you use document search tools.

**Q: Can I use other LLM providers (OpenAI, Claude)?**
A: Currently, only Gemini and Ollama are supported. You can extend `modules/model_manager.py` to add more providers.

**Q: Is my conversation data stored?**
A: Yes, in the `memory/` folder, organized by date. Each session has a unique ID.

**Q: Can I delete old sessions?**
A: Yes, just delete the corresponding folders in `memory/`. This won't affect the agent's operation.

**Q: How do I update the agent?**
A: If you received new code, replace the files and run:
```bash
uv sync  # or pip install --upgrade -r requirements.txt
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check the logs**: Look at the terminal output carefully
2. **Verify configuration**: Ensure `config/profiles.yaml` and `.env` are correct
3. **Test dependencies**: Run `python -c "import asyncio, faiss, httpx, mcp"`
4. **Search the code**: Use comments in the code to understand specific functions
5. **Ask for help**: Provide the error message and steps you took

---

## Summary

You now have a complete understanding of the Cortex-R AI Agent! Here's a quick recap:

1. **Install**: Python 3.11+, dependencies via `uv sync`, API keys in `.env`
2. **Configure**: Update paths in `config/profiles.yaml`, choose model in `config/models.json`
3. **Run**: `python agent.py`
4. **Test**: Try simple queries first, then complex multi-step tasks
5. **Debug**: Read logs, check memory, verify configuration
6. **Extend**: Add new tools to MCP servers, adjust strategy in profiles.yaml

Happy coding! 🚀
