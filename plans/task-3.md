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

method (string)  
HTTP method such as:

GET  
POST  
PUT  
DELETE

path (string)  
API path such as:

/items/  
/analytics/completion-rate

body (string, optional)  
JSON string used as the request body.

---

## Return Format

The tool returns a JSON string:
{
“status_code”: 200,
“body”: {…}
}
---

# Authentication

The API requires authentication using `LMS_API_KEY`.

The key is provided via environment variables:
LMS_API_KEY
The agent will include it in requests using the header:
Authorization: Bearer <LMS_API_KEY>
---

# API Base URL

The base URL must come from an environment variable:
AGENT_API_BASE_URL
Default value:
http://localhost:42005
This ensures compatibility with the autochecker environment.

---

# Updated System Prompt Strategy

The system prompt will instruct the LLM to decide which tool to use:

Use **read_file** when:
- the question refers to documentation
- the question refers to source code
- debugging a crash or bug

Use **list_files** when:
- discovering project structure

Use **query_api** when:
- retrieving live data
- checking API responses
- testing endpoints

The agent may combine tools when diagnosing errors.

Example workflow:

1. call `query_api`
2. see error message
3. read source code with `read_file`
4. explain the bug

---

# Benchmark Iteration

Initial run:
uv run run_eval.py
Example first result:
3/10 passed
Failures usually occur because:

- the LLM doesn't select the correct tool
- tool descriptions are unclear
- the system prompt does not guide reasoning well

---

# Iteration Strategy

1. Improve tool descriptions.
2. Make system prompt explicit about when to use each tool.
3. Ensure tool results are returned in full.
4. Ensure the agent correctly parses tool responses.

Continue running:
uv run run_eval.py
until all **10 questions pass locally**.

---

# Goal

The final agent should be able to:

- read documentation
- inspect source code
- query live API data
- diagnose bugs using multiple tools

This creates a fully capable **multi-tool reasoning agent**.
