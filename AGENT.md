## Tools

The agent has three tools for interacting with the project and backend system.

### list_files

Lists files and directories at a given path.

**Parameters:**

- `path` (string) - Relative path to directory, e.g., `wiki/`, `backend/app/routers/`

**Returns:** Newline-separated file list.

**Use when:** Exploring project structure, discovering files, finding modules.

### read_file

Reads the contents of a file in the repository.

**Parameters:**

- `path` (string) - Relative path to file, e.g., `wiki/git-workflow.md`, `backend/app/main.py`

**Returns:** File contents as text.

**Use when:** Reading documentation, source code, configuration files, or diagnosing bugs.

### query_api

Sends an HTTP request to the running backend API.

**Parameters:**

- `method` (string) - HTTP method: GET, POST, PUT, DELETE
- `path` (string) - API endpoint path, e.g., `/items/`, `/analytics/completion-rate`
- `body` (string, optional) - JSON string for request body (POST/PUT)

**Returns:** JSON string with `status_code` and `body` fields.

**Authentication:** Uses `LMS_API_KEY` from environment variables with Bearer token auth.

**Use when:** Querying live data (item counts, analytics), checking API responses, testing endpoints, diagnosing runtime errors.

---

## Environment Variables

The agent reads all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for backend (default: `http://localhost:42002`) | Optional env var |

**Important:** The autochecker injects its own values during evaluation. Never hardcode these values.

---

## Agentic Loop

The agent uses an iterative reasoning loop:

1. Send the user question and tool schemas to the LLM.
2. The LLM may return tool calls.
3. The agent executes each tool locally.
4. Tool results are added to the conversation as tool messages.
5. The updated conversation is sent back to the LLM.
6. The loop continues until the LLM returns a final answer (no tool calls).

A maximum of 10 tool calls is allowed per question.

---

## System Prompt Strategy

The system prompt instructs the LLM to select tools based on question type:

**Use `read_file` for:**

- Documentation in `wiki/`
- Source code files
- Framework/library identification
- Architecture questions
- Configuration files
- Bug diagnosis (after seeing the error)

**Use `list_files` for:**

- Discovering project structure
- Finding router modules
- Exploring directories

**Use `query_api` for:**

- Live data queries (item counts, scores)
- API status code questions
- Analytics endpoints
- Runtime state questions

**Bug diagnosis workflow:**

1. Call `query_api` to reproduce the error
2. Read the error message in the response
3. Call `read_file` on the relevant source file
4. Identify and explain the bug

---

## Tool Decision Logic

The LLM decides which tool to use based on the question semantics:

- **Wiki/documentation questions** → `list_files` on `wiki/`, then `read_file`
- **Source code questions** → `read_file` directly on the file path
- **Live data questions** → `query_api` (never use documentation for runtime data)
- **Status code questions** → `query_api` to make the actual request
- **Bug diagnosis** → `query_api` first, then `read_file`

This separation ensures the agent distinguishes between static knowledge (documentation, code) and dynamic knowledge (database state, API responses).

---

## Lessons Learned from Benchmark

During benchmark iteration, several issues were identified and fixed:

1. **Tool description clarity:** Initially, tool descriptions were too vague. Adding explicit examples and use cases in the schema helped the LLM select the right tool.

2. **System prompt specificity:** The original prompt didn't clearly distinguish when to use `query_api` vs `read_file`. Adding a structured decision tree improved tool selection accuracy.

3. **Content null handling:** The LLM sometimes returns `content: null` when making tool calls. Using `(msg.get("content") or "")` instead of `msg.get("content", "")` handles this edge case.

4. **API authentication:** The `query_api` tool must include the `LMS_API_KEY` in the Authorization header. Forgetting this causes 401 errors on all API calls.

5. **Environment variable separation:** `LMS_API_KEY` (backend) and `LLM_API_KEY` (LLM provider) serve different purposes. Mixing them up causes authentication failures.

---

## Final Evaluation Score

After iteration, the agent passes all 10 local benchmark questions:

- Wiki lookup questions (branch protection, SSH)
- System facts (FastAPI framework, router modules)
- Data queries (item count, status codes)
- Bug diagnosis (ZeroDivisionError, TypeError)
- Reasoning questions (request lifecycle, ETL idempotency)

The agent correctly chains tools for multi-step questions, such as querying an API endpoint to see an error, then reading the source code to identify the root cause.
