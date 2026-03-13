import sys
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")


def call_llm(question: str) -> str:
    url = f"{API_BASE}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Answer briefly."},
            {"role": "user", "content": question},
        ],
        "temperature": 0,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


def main():
    if len(sys.argv) < 2:
        print("No question provided", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    try:
        answer = call_llm(question)

        result = {
            "answer": answer,
            "tool_calls": []
        }

        print(json.dumps(result))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
