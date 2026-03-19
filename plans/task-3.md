# Task 3 Plan – System Agent

## Overview

In this task the agent will be extended with a new tool called `query_api`.
This tool allows the agent to interact directly with the deployed backend API.

The goal is to allow the agent to answer:

1. **Static system questions**
   - framework used
   - router modules
   - HTTP status codes

2. **Data-dependent questions**
   - item counts
   - analytics endpoints
   - completion rate
   - learner statistics

The agent will combine three knowledge sources:

- project documentation (wiki files)
- source code
- the running backend API

---

# query_api Tool

## Purpose

`query_api` allows the agent to send HTTP requests to the running backend.

This makes the agent capable of retrieving **live system data** instead of relying on documentation.

---

## Parameters

- `method` (string): HTTP method such as GET, POST, PUT, DELETE
- `path` (string): API path such as `/items/`, `/analytics/completion-rate`
- `body` (string, optional): JSON string used as the request body
- `auth` (string, optional): Auth token. Use "none" to skip authentication.

---

## Return Format

The tool returns a JSON string:

```json
{
  "status_code": 200,
  "body": {...}
}
```

---

# Authentication

The API requires authentication using `LMS_API_KEY`.

The key is provided via environment variables:

- `LMS_API_KEY` from `.env.docker.secret`
- The agent includes it in requests using the header: `Authorization: Bearer <LMS_API_KEY>`

---

# API Base URL

The base URL comes from environment variable:

- `AGENT_API_BASE_URL` (default: `http://localhost:42002`)

This ensures compatibility with the autochecker environment.

---

# Updated System Prompt Strategy

The system prompt instructs the LLM to decide which tool to use:

**Use `read_file` when:**

- the question refers to documentation
- the question refers to source code
- debugging a crash or bug

**Use `list_files` when:**

- discovering project structure

**Use `query_api` when:**

- retrieving live data
- checking API responses
- testing endpoints
- testing authentication (use `auth="none"`)

The agent may combine tools when diagnosing errors.

Example workflow:

1. call `query_api`
2. see error message
3. read source code with `read_file`
4. explain the bug

---

# Benchmark Iteration

Initial run:

```bash
uv run run_eval.py
```

Failures usually occur because:

- the LLM doesn't select the correct tool
- tool descriptions are unclear
- the system prompt does not guide reasoning well
- the LLM doesn't complete its answers

---

# Iteration Strategy

1. Improve tool descriptions.
2. Make system prompt explicit about when to use each tool.
3. Ensure tool results are returned in full.
4. Ensure the agent correctly parses tool responses.
5. Add error handling for edge cases.

Continue running `uv run run_eval.py` until all **10 questions pass locally**.

---

# Goal

The final agent should be able to:

- read documentation
- inspect source code
- query live API data
- diagnose bugs using multiple tools

This creates a fully capable **multi-tool reasoning agent**.

---

# Implementation Progress

## Completed

1. **query_api tool implemented** - Sends HTTP requests to backend with Bearer token auth
2. **Environment variables** - All config read from `.env.agent.secret` and `.env.docker.secret`
3. **System prompt updated** - Clear guidance on when to use each tool
4. **Tool schemas improved** - Added descriptions and examples for each tool
5. **Source tracking** - Agent now tracks files read for source field in output
6. **Rate limit handling** - Added exponential backoff retry logic for 429 responses
7. **Documentation** - AGENT.md updated with full architecture and lessons learned
8. **Tests** - Created `tests/test_agent_tools.py` with 2 regression tests
9. **Auth parameter** - Added `auth` parameter to query_api for testing unauthenticated access
10. **Error handling** - Added handling for empty/invalid tool arguments

## Benchmark Status

**Final Score: 7/10 passed**

### Passing Questions (7)

1. ✓ Wiki: Branch protection steps
2. ✓ Wiki: SSH connection steps  
3. ✓ Source code: FastAPI framework
4. ✓ Source code: API router modules
5. ✓ Query API: Item count
6. ✓ Query API: Status code without auth (401)
7. ✓ Query + Read: ZeroDivisionError in completion-rate

### Failing Questions (3)

8. ✗ Query + Read: TypeError in top-learners (LLM doesn't complete answer)
2. ✗ Read: Request lifecycle (LLM doesn't complete answer)
3. ✗ Read: ETL idempotency (LLM doesn't complete answer)

## Issues Identified

1. **LLM Answer Completion:** The Qwen3 Coder Plus model sometimes doesn't complete its answers, leaving responses like "Let me also check..." without finishing. This is a model limitation.

2. **Tool Argument Parsing:** Added error handling for empty/invalid tool arguments.

3. **Authentication Handling:** Added `auth` parameter to `query_api` to test unauthenticated endpoints.

## Iteration History

1. Added `query_api` tool with authentication
2. Improved system prompt with explicit tool selection guidance
3. Added source tracking for file references
4. Added retry logic for rate limiting (when using OpenRouter)
5. Fixed auth parameter handling for testing unauthenticated access
6. Added error handling for empty tool arguments
7. Increased max tool iterations from 10 to 15
8. Set up Qwen Code API on VM (10.93.24.223:42005)

## Next Steps

To improve the score:

1. Consider using a more capable LLM model
2. Add more explicit instructions for completing answers
3. Potentially add post-processing to extract answers from incomplete responses

---

## Agent Architecture Summary

The agent uses an agentic loop with:

- **3 tools:** `list_files`, `read_file`, `query_api`
- **LLM:** Qwen3 Coder Plus (via Qwen Code API on VM at 10.93.24.223:42005)
- **Max iterations:** 15 tool calls per question
- **Output format:** JSON with `answer`, `tool_calls`, and optional `source`
