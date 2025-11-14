# Gemini Agent Architecture: A Guide for Stakeholders

Welcome to the architectural overview of our Gemini-powered AI agent. This document is designed for a non-technical audience, providing a clear and simple explanation of how our AI system is structured and how it works.

---

## 1. Introduction: The AI with a Thousand Tools

Imagine an AI that's not just a conversationalist, but a problem-solver. That's the essence of this system. It's an AI agent that can understand your goals, create a plan to achieve them, and use a variety of tools to get the job done.

Think of it as a digital assistant with a versatile toolkit. It can perform calculations, search the web, and even read through your documents to find the information you need. The "brain" of this assistant is powered by Google's Gemini Pro, giving it advanced reasoning and language capabilities.

---

## 2. How It Thinks: A 3-Step Symphony

At the heart of the agent's operation is a simple yet powerful 3-step process, often called the **Perception-Decision-Action loop**.

1.  **Perception (See):** First, the agent *perceives* the world around it. This means understanding your request, the context of the conversation, and the tools it has at its disposal.

2.  **Decision (Think):** Next, the agent *thinks* about what to do. Based on its perception, it decides on the best course of action. This involves creating a step-by-step plan to address your request.

3.  **Action (Do):** Finally, the agent *acts*. It executes the plan it created, which may involve using one or more of its tools.

This loop repeats as many times as needed until your request is fully resolved.

---

## 3. Anatomy of the Agent: The Key Components

Our AI system is composed of several distinct components, each with a specific role. This modular design makes the system robust, scalable, and easy to maintain.

### The Conductor (`agent.py`)

This is the main entry point of the application. It's the "conductor" of our AI orchestra, responsible for starting the system, managing the user interaction, and ensuring that all the other components work together in harmony.

### The Core Engine (`core/` directory)

This directory contains the fundamental logic of the agent.

*   **`loop.py`:** This file implements the 3-step symphony (Perception-Decision-Action loop) described above. It's the engine that drives the agent's thinking process.
*   **`session.py`:** This file manages the agent's "session," which includes everything related to the current conversation, such as the history of interactions and the tools that are available.
*   **`context.py`:** This file holds the "context" of the agent's current state, including its memory and configuration.

### The "Senses" and "Mind" (`modules/` directory)

This directory contains the "cognitive" modules of the agent.

*   **`perception.py`:** This is the agent's "senses." It's responsible for understanding your request and the current situation.
*   **`decision.py`:** This is the agent's "mind." It's where the agent makes decisions and creates plans.
*   **`action.py`:** This is how the agent interacts with the world. It executes the plans created by the decision module.
*   **`memory.py`:** This is the agent's memory. It allows the agent to remember past interactions and learn from them.

### The Toolbox (`mcp_server_*.py` files)

The agent's tools are provided by a set of "MCP servers." MCP stands for **Model Context Protocol**, which is a standardized way for the agent to communicate with its tools. Each MCP server is a separate program that provides a specific set of capabilities.

*   **`mcp_server_1.py` (The Calculator):** This server provides tools for performing mathematical calculations.
*   **`mcp_server_2.py` (The Librarian):** This server provides tools for reading and searching through documents. This is a key part of our **Retrieval-Augmented Generation (RAG)** capabilities, which allow the agent to use your documents as a knowledge source.
*   **`mcp_server_3.py` (The Web Surfer):** This server provides tools for searching the web.

### The Memory (`memory/` directory)

This directory is where the agent stores its long-term memory. Every conversation is saved as a JSON file, creating a detailed log of the agent's activities. This is invaluable for auditing, debugging, and future improvements.

### The Rulebook (`config/` and `prompts/` directories)

*   **`config/`:** This directory contains configuration files that define the agent's behavior. The most important file is `profiles.yaml`, which specifies which tools the agent can use, how it should behave, and which AI model it should use.
*   **`prompts/`:** This directory contains text files that serve as "prompts" for the Gemini Pro model. These prompts are carefully crafted instructions that guide the AI's reasoning process, ensuring that it behaves in a predictable and desirable way.

---

## 4. The Flow of a Request: From Question to Answer

Let's walk through a simple example to see how all these components work together.

**Your Request:** "What is 2 plus 2?"

1.  **The `agent.py` conductor starts the process.** It receives your request and initiates the Perception-Decision-Action loop.

2.  **Perception:** The `perception.py` module analyzes your request and determines that you want to perform an addition. It also recognizes that the "calculator" tool server (`mcp_server_1.py`) will be needed.

3.  **Decision:** The `decision.py` module creates a simple plan: "Use the `add` tool from the calculator server with the numbers 2 and 2."

4.  **Action:** The `action.py` module executes the plan. It sends a request to the `mcp_server_1.py` server, asking it to use the `add` tool with the numbers 2 and 2.

5.  **Tool Execution:** The `mcp_server_1.py` server receives the request, performs the addition, and sends the result (4) back to the action module.

6.  **Response:** The agent now has the answer. It formats the response and displays it to you: "The answer is 4."

7.  **Memory:** The entire interaction is saved to a file in the `memory/` directory.

---

## 5. The Power of Tools: The MCP Servers

The MCP server architecture is a key feature of our system. By running each set of tools as a separate server, we gain several advantages:

*   **Modularity:** We can add new tools and capabilities without having to modify the core agent logic.
*   **Scalability:** We can run the tool servers on different machines, allowing us to scale the system to handle more complex tasks.
*   **Robustness:** If one tool server crashes, it doesn't bring down the entire system.

---

## 6. Making It Your Own: Configuration and Customization

One of the most powerful aspects of our AI agent is its configurability. By editing the `config/profiles.yaml` file, you can customize many aspects of the agent's behavior, including:

*   **The AI Model:** You can switch to different AI models, including other versions of Gemini or even models that you run on your own computer.
*   **The Tools:** You can add or remove tool servers, or even create your own custom tools.
*   **The Strategy:** You can change the agent's problem-solving strategy, making it more "conservative" or "exploratory."

---

## 7. Glossary of Terms

*   **AI Agent:** An autonomous program that can perceive its environment, make decisions, and take actions to achieve its goals.
*   **Gemini Pro:** A powerful AI model from Google that provides the agent's reasoning and language capabilities.
*   **MCP (Model Context Protocol):** A standardized way for the agent to communicate with its tools.
*   **RAG (Retrieval-Augmented Generation):** A technique that allows the agent to use your documents as a knowledge source.
*   **Sandbox:** A safe, isolated environment where the agent executes its plans, preventing it from causing any harm to the system.

---

## 8. How to Contribute

We welcome contributions from everyone, regardless of their technical background. If you have an idea for a new feature, a suggestion for improving the documentation, or you've found a bug, please let us know.

For developers who want to contribute code, the best place to start is by looking at the `mcp_server_*.py` files. Creating a new tool server is a great way to add new capabilities to the agent.

Thank you for taking the time to learn about our AI agent's architecture. We're excited about the possibilities that this system unlocks, and we look forward to seeing what you'll build with it.
