import sys
import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

# load env files if present
load_dotenv(".env.agent.secret")
load_dotenv(".env.docker.secret")

# LLM configuration
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL")

# backend configuration
LMS_API_KEY = os.getenv("LMS_API_KEY")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

PROJECT_ROOT = Path(".").resolve()

tool_history = []
source_files = []


# -----------------------------
# Path security helper
# -----------------------------
def safe_path(path_str):
    path = (PROJECT_ROOT / path_str).resolve()

    if not str(path).startswith(str(PROJECT_ROOT)):
        raise ValueError("Access outside project directory not allowed")

    return path


# -----------------------------
# Tool: read_file
# -----------------------------
def read_file(path):
    try:
        file_path = safe_path(path)

        if not file_path.exists():
            return "Error: file does not exist"

        return file_path.read_text()

    except Exception as e:
        return f"Error: {str(e)}"


# -----------------------------
# Tool: list_files
# -----------------------------
def list_files(path):
    try:
        dir_path = safe_path(path)

        if not dir_path.exists():
            return "Error: directory does not exist"

        entries = os.listdir(dir_path)

        return "\n".join(entries)

    except Exception as e:
        return f"Error: {str(e)}"


# -----------------------------
# Tool: query_api
# -----------------------------
def query_api(method, path, body=None, auth="__DEFAULT__"):
    try:
        url = f"{AGENT_API_BASE_URL}{path}"

        headers = {
            "Content-Type": "application/json",
        }

        # Add auth header based on auth parameter
        # auth="__DEFAULT__" means use LMS_API_KEY from env
        # auth="none" or auth=None means no authentication
        # auth="<token>" means use the provided token
        if auth == "__DEFAULT__":
            if LMS_API_KEY:
                headers["Authorization"] = f"Bearer {LMS_API_KEY}"
        elif auth is not None and auth != "none":
            headers["Authorization"] = f"Bearer {auth}"
        # else: no auth header

        data = None
        if body:
            data = json.loads(body)

        with httpx.Client() as client:
            response = client.request(
                method,
                url,
                headers=headers,
                json=data,
                timeout=30
            )

        result = {
            "status_code": response.status_code,
            "body": response.text
        }

        return json.dumps(result)

    except Exception as e:
        return json.dumps({"error": str(e)})


# -----------------------------
# Tool schemas for LLM
# -----------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a project path. Use to discover files, explore directory structure, or find modules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to directory, e.g., 'wiki/', 'backend/app/routers/'"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file in the project. Use for documentation, source code, config files, or any text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file, e.g., 'wiki/git-workflow.md', 'backend/app/main.py'"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Send an HTTP request to the running backend API. Use for live data: item counts, API status codes, analytics, runtime state. NOT for documentation or source code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE"},
                    "path": {"type": "string", "description": "API endpoint path, e.g., '/items/', '/analytics/completion-rate'"},
                    "body": {"type": "string", "description": "Optional JSON string for request body (POST/PUT)"},
                    "auth": {"type": "string", "description": "Optional auth token. Leave unspecified to use default key. Set to 'none' to skip authentication."}
                },
                "required": ["method", "path"]
            }
        }
    }
]


# -----------------------------
# Call LLM
# -----------------------------
def call_llm(messages):

    url = f"{LLM_API_BASE}/chat/completions"

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "temperature": 0
    }

    # Retry with exponential backoff for rate limits
    max_retries = 10
    backoff = 3.0

    for attempt in range(max_retries):
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 429:
            import time
            # Get retry-after header if present
            retry_after = response.headers.get("retry-after")
            if retry_after:
                wait_time = float(retry_after)
            else:
                wait_time = backoff * (attempt + 1)
            print(f"Rate limited, waiting {wait_time}s...", file=sys.stderr)
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        return response.json()["choices"][0]["message"]

    raise Exception("Max retries exceeded due to rate limiting")


# -----------------------------
# Execute tool
# -----------------------------
def execute_tool(name, args):

    global source_files

    if name == "read_file":
        result = read_file(**args)
        # Track source file for documentation questions
        if result and not result.startswith("Error:"):
            source_files.append(args.get("path", ""))

    elif name == "list_files":
        result = list_files(**args)

    elif name == "query_api":
        result = query_api(**args)

    else:
        result = "Unknown tool"

    tool_history.append({
        "tool": name,
        "args": args,
        "result": result
    })

    return result


# -----------------------------
# Main agent loop
# -----------------------------
def main():

    global tool_history, source_files

    if len(sys.argv) < 2:
        print("No question provided", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Reset state for each run
    tool_history = []
    source_files = []

    system_prompt = """
You are a system analysis agent for a software engineering lab project.

You have three tools to answer questions about the project:

**list_files** - List files and directories in a path
**read_file** - Read file contents from the repository
**query_api** - Send HTTP requests to the running backend API

## When to use each tool:

### Use read_file when the question asks about:
- Documentation in the wiki/ directory
- Source code files (backend/, agent.py, docker-compose.yml, etc.)
- Frameworks, libraries, or technologies used
- Architecture, design patterns, or code structure
- Configuration files (Dockerfile, pyproject.toml, etc.)
- Bug diagnosis (read the error, then read the source code)

### Use list_files when you need to:
- Discover what files exist in a directory
- Find API router modules
- Explore project structure

### Use query_api when the question asks about:
- Live data from the running system (e.g., "how many items")
- API responses and status codes
- Analytics endpoints (/analytics/*)
- Runtime behavior or current state
- Testing authentication (use auth="none" to test without auth)

## Important guidelines:

1. For API questions, always use query_api - do not try to read documentation for live data.

2. For status codes, use query_api to make the actual request and observe the response.

3. If an API endpoint returns an error, use query_api first to see the error, then use read_file to examine the source code and identify the bug.

4. For questions about the wiki, use list_files on wiki/ then read_file on relevant files.

5. For questions about source code, use read_file directly on the file path.

6. When diagnosing bugs: (1) query the endpoint to see the error, (2) read the source code to find the bug.

7. To test API without authentication: use query_api with auth="none" parameter.

8. When investigating crashes: Query the endpoint with realistic parameters to trigger the actual error. Read the error message carefully - it tells you the exact error type (TypeError, ZeroDivisionError, etc.) and line number.

9. Be efficient: batch your tool calls when possible. For example, if you need to read multiple files, call them in parallel.

8. Complete your answer: After gathering all information, provide a complete final answer. Don't say "let me continue" - finish the task.

9. For "list all routers" questions: First use list_files on the routers directory, then read ALL router files, then provide a complete summary of each router's domain.

10. IMPORTANT: When you have enough information, return your final answer immediately. Do not say "let me read more" - just provide the complete answer based on what you've already learned.

11. AFTER using list_files to discover files, you should read ALL the files in ONE batch (parallel tool calls), then provide your complete answer. Do not read files one at a time.

12. Your final answer should directly answer the question. For router questions, list each router file and its domain (e.g., "items.py - handles CRUD operations for learning items").

Return your final answer as JSON with an "answer" field. Include a "source" field when the answer comes from a specific file.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_count = 0

    while tool_count < 15:

        msg = call_llm(messages)

        # if no tool calls -> final answer
        if not msg.get("tool_calls"):

            content = msg.get("content") or ""

            try:
                parsed = json.loads(content)
                answer = parsed.get("answer", content)
                source = parsed.get("source")
            except Exception:
                answer = content
                source = None

            # Use tracked source files if no explicit source provided
            if not source and source_files:
                source = source_files[0]

            output = {
                "answer": answer,
                "tool_calls": tool_history
            }

            if source:
                output["source"] = source

            print(json.dumps(output))
            return

        messages.append(msg)

        for tool_call in msg["tool_calls"]:

            name = tool_call["function"]["name"]
            args_str = tool_call["function"]["arguments"]
            
            # Handle empty or invalid arguments
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}

            result = execute_tool(name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result
            })

            tool_count += 1

    # tool limit reached
    print(json.dumps({
        "answer": "Unable to complete request within tool limit.",
        "tool_calls": tool_history
    }))


if __name__ == "__main__":
    main()
