## Tools

The agent has two tools for interacting with the repository.

### list_files

Lists files and directories at a given path.

Parameters:
- path (string)

Returns:
newline-separated file list.

### read_file

Reads the contents of a file in the repository.

Parameters:
- path (string)

Returns:
file contents as text.

Both tools enforce path security and cannot access files outside the project directory.

---

## Agentic Loop

The agent uses an iterative reasoning loop:

1. Send the user question and tool schemas to the LLM.
2. The LLM may return tool calls.
3. The agent executes each tool locally.
4. Tool results are added to the conversation.
5. The updated conversation is sent back to the LLM.
6. The loop continues until the LLM returns a final answer.

A maximum of 10 tool calls is allowed.

---

## System Prompt Strategy

The system prompt instructs the LLM to:

- explore the `wiki/` directory using `list_files`
- read documentation files using `read_file`
- locate the section that answers the question
- return an answer with a source reference
