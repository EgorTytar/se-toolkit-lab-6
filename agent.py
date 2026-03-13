import sys
import os
import json
import requests
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
API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

PROJECT_ROOT = Path(".").resolve()

tool_history = []


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
def query_api(method, path, body=None):
    try:
        url = f"{API_BASE_URL}{path}"

        headers = {
            "Authorization": f"Bearer {LMS_API_KEY}",
            "Content-Type": "application/json",
        }

        data = None
        if body:
            data = json.loads(body)

        response = requests.request(
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
            "description": "List files and directories in the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the repository such as wiki or source code",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend API to retrieve live system data",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string"},
                    "path": {"type": "string"},
                    "body": {"type": "string"}
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

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    response.raise_for_status()

    return response.json()["choices"][0]["message"]


# -----------------------------
# Execute tool
# -----------------------------
def execute_tool(name, args):

    if name == "read_file":
        result = read_file(**args)

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

    if len(sys.argv) < 2:
        print("No question provided", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    system_prompt = """
You are a system analysis agent for a software project.

You can use tools to answer questions about the project.

Available tools:

list_files
Use this to explore project directories.

read_file
Use this to read documentation or source code.

query_api
Use this to query the running backend API for live data.

Use read_file when answering questions about:
- project documentation
- source code
- frameworks used
- architecture

Use list_files to discover files or modules.

Use query_api when answering questions about:
- database item counts
- API responses
- analytics endpoints
- runtime system data.

If an API endpoint fails, query the endpoint first and then read the source code to diagnose the issue.

Return a clear answer. Include a source reference when the answer comes from documentation.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_count = 0

    while tool_count < 10:

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
            args = json.loads(tool_call["function"]["arguments"])

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
