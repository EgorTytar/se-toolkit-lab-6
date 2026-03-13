def test_merge_conflict_question():
    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        timeout=60
    )

    data = json.loads(result.stdout)

    assert "tool_calls" in data
    assert any(tc["tool"] == "read_file" for tc in data["tool_calls"])


def test_list_files_question():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki?"],
        capture_output=True,
        text=True,
        timeout=60
    )

    data = json.loads(result.stdout)

    assert any(tc["tool"] == "list_files" for tc in data["tool_calls"])
def test_framework_detection():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What framework does the backend use?"],
        capture_output=True,
        text=True,
        timeout=60
    )

    data = json.loads(result.stdout)

    assert any(tc["tool"] == "read_file" for tc in data["tool_calls"])
def test_database_query():
    result = subprocess.run(
        ["uv", "run", "agent.py", "How many items are in the database?"],
        capture_output=True,
        text=True,
        timeout=60
    )

    data = json.loads(result.stdout)

    assert any(tc["tool"] == "query_api" for tc in data["tool_calls"])
