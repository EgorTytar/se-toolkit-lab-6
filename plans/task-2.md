# Task 2 Plan – Documentation Agent

## Overview

In this task the agent will be extended with tools and an agentic loop so that it can read documentation from the project repository.

The agent will be able to:
- discover documentation files
- read their contents
- extract the answer to the user's question
- return the answer along with a source reference

Two tools will be implemented: `list_files` and `read_file`.

---

# Tool Schemas

The tools will be defined using the OpenAI-compatible function calling schema.

## list_files

Purpose:
List files and directories in a given path.

Parameters:
- path (string) – relative directory path from the project root.

Returns:
- newline-separated list of files and directories.

Example output:
git-workflow.md
docker.md
api.md
---

## read_file

Purpose:
Read the contents of a file in the repository.

Parameters:
- path (string) – relative file path from project root.

Returns:
- file contents as a string.

If the file does not exist, the tool returns an error message.

---

# Agentic Loop

The agent will follow this workflow:

1. Receive the user's question from the CLI.
2. Send the question and tool definitions to the LLM.
3. The LLM decides whether to:
   - call a tool
   - return the final answer.
4. If the LLM returns `tool_calls`:
   - execute each tool locally
   - append the tool result as a message
   - send the updated conversation back to the LLM.
5. Repeat until:
   - the LLM returns a final message without tool calls, or
   - the maximum of **10 tool calls** is reached.

The final message should contain:
- the answer
- the source reference (wiki path + anchor).

---

# Path Security

To prevent directory traversal attacks, tools will enforce strict path validation.

Security rules:

- All paths must stay within the project root.
- `../` traversal is not allowed.
- Paths will be resolved using `Path.resolve()` and compared against the project root.
- If a path escapes the root directory, the tool will return an error.

This prevents the agent from accessing sensitive system files.

---

# Output Format

The CLI must output a single JSON object:
{
“answer”: “…”,
“source”: “wiki/file.md#section”,
“tool_calls”: […]
}
Fields:

- `answer` – final response from the LLM
- `source` – documentation reference
- `tool_calls` – list of executed tools including arguments and results

Maximum of **10 tool calls per request**.

---

# System Prompt Strategy

The system prompt will instruct the LLM to:

1. Use `list_files` to explore the `wiki/` directory.
2. Use `read_file` to read documentation files.
3. Find the section that answers the question.
4. Return the answer with a `source` reference pointing to the correct wiki section.

This encourages the LLM to reason about documentation rather than hallucinating answers.
