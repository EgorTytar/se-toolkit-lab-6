import sys
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

PROJECT_ROOT = Path(".").resolve()

tool_history = []


def safe_path(path_str):
    path = (PROJECT_ROOT / path_str).resolve()
    if not str(path).startswith(str(PROJECT_ROOT)):
        raise ValueError("Access outside project directory is not allowed")
    return path


def read_file(path):
    try:
        file_path = safe_path(path)

        if not file_path.exists():
            return "Error: file does not exist"

        return file_path.read_text()

    except Exception as e:
        return f"Error: {str(e)}"


def list_files(path):
    try:
        dir_path = safe_path(path)

        if not dir_path.exists():
            return "Error: directory does not exist"

        entries = os.listdir(dir_path)
        return "\n".join(entries)

    except Exception as e:
        return f"Error: {str(e)}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
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
            "description": "Read a file from the repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    }
]


def call_llm(messages):
    url = f"{API_BASE}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "temperature": 0,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()

    return r.json()["choices"][0]["message"]


def execute_tool(name, args):
    if name == "list_files":
        result = list_files(**args)
    elif name == "read_file":
        result = read_file(**args)
    else:
        result = "Unknown tool"

    tool_history.append({
        "tool": name,
        "args": args,
        "result": result
    })

    return result


def main():
    if len(sys.argv) < 2:
        print("No question provided", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    system_prompt = """
You are a documentation agent.

Use list_files to explore the wiki folder.
Use read_file to read documentation.

Find the answer in the wiki and return the answer with a source reference.

The source must include the wiki file path and section anchor.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_count = 0

    while tool_count < 10:
        message = call_llm(messages)

        if "tool_calls" not in message:
            content = message.get("content", "")

            try:
                data = json.loads(content)
                answer = data.get("answer", content)
                source = data.get("source", "")
            except:
                answer = content
                source = ""

            output = {
                "answer": answer,
                "source": source,
                "tool_calls": tool_history
            }

            print(json.dumps(output))
            return

        messages.append(message)

        for tool_call in message["tool_calls"]:
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])

            result = execute_tool(name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result
            })

            tool_count += 1

    print(json.dumps({
        "answer": "Unable to complete within tool limit.",
        "source": "",
        "tool_calls": tool_history
    }))


if __name__ == "__main__":
    main()
