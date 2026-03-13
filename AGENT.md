# Agent Documentation

## Overview

This project implements a simple CLI agent that connects to a Large Language Model (LLM) using an OpenAI-compatible API.

The agent receives a user question from the command line, sends it to an LLM, and returns a structured JSON response.

Example: uv run agent.py “What does REST stand for?”
{“answer”: “Representational State Transfer.”, “tool_calls”: []}

## LLM Provider

This agent uses the **Qwen Code API**.

Model used:

qwen3-coder-plus

The API is OpenAI-compatible, allowing standard chat completion requests.

## Configuration

The agent reads configuration values from:

.env.agent.secret

Required variables:
LLM_API_KEY
LLM_API_BASE
LLM_MODEL

Example:
LLM_API_KEY=your_api_key
LLM_API_BASE=https://api.qwen.ai/v1
LLM_MODEL=qwen3-coder-plus

## How the Agent Works

1. The user provides a question as a CLI argument.
2. The program loads environment variables.
3. A request is sent to the LLM chat completions API.
4. The LLM generates an answer.
5. The program outputs structured JSON.

Output format:
{
“answer”: “…”,
“tool_calls”: []
}
## Output Rules

- Only JSON is written to stdout.
- Debug and errors are written to stderr.
- Exit code 0 on success.

## Running the Agent

Example command:
uv run agent.py “What is HTTP?”

## Testing

Run the regression tests with:

pytest

The tests verify that the agent returns valid JSON with the required fields.


