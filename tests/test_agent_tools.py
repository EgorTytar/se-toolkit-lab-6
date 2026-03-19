"""Regression tests for agent tool usage.

These tests verify that the agent uses the correct tools for different question types.
"""

import json
import subprocess
import pytest


def run_agent(question: str, timeout: int = 120) -> dict:
    """Run the agent with a question and return parsed output."""
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    data = json.loads(result.stdout)
    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    
    return data


def get_tools_used(data: dict) -> set:
    """Extract set of tool names used by the agent."""
    tool_calls = data.get("tool_calls", [])
    return {tc.get("tool") for tc in tool_calls if tc.get("tool")}


class TestAgentToolUsage:
    """Tests verifying correct tool usage for different question types."""
    
    def test_framework_question_uses_read_file(self):
        """Question about backend framework should use read_file tool.
        
        The agent should read source code (e.g., backend/app/main.py) 
        to identify that FastAPI is used.
        """
        question = "What Python web framework does this project's backend use?"
        
        data = run_agent(question)
        tools_used = get_tools_used(data)
        
        assert "read_file" in tools_used, (
            f"Expected 'read_file' tool for framework question. "
            f"Tools used: {tools_used}. Answer: {data.get('answer', '')}"
        )
        
        # Verify answer mentions FastAPI
        answer = data.get("answer", "").lower()
        assert "fastapi" in answer, (
            f"Answer should mention FastAPI. Got: {data.get('answer', '')}"
        )
    
    def test_item_count_question_uses_query_api(self):
        """Question about item count should use query_api tool.
        
        The agent should query GET /items/ to get live data from the database.
        """
        question = "How many items are currently stored in the database?"
        
        data = run_agent(question)
        tools_used = get_tools_used(data)
        
        assert "query_api" in tools_used, (
            f"Expected 'query_api' tool for item count question. "
            f"Tools used: {tools_used}. Answer: {data.get('answer', '')}"
        )
        
        # Verify answer contains a number
        import re
        answer = data.get("answer", "")
        numbers = re.findall(r"\d+", answer)
        assert len(numbers) > 0, (
            f"Answer should contain a number. Got: {answer}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
