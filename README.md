# Second Brain — AI-Powered Notion Task Agent

> A personal experiment in building an autonomous task-capture system using the OpenAI SDK, ChatGPT Custom GPT Actions, the Notion API, and the Model Context Protocol (MCP).

---

## What This Is

This project started as a question: *can I talk to an AI and have it automatically organise my tasks into Notion — without me ever opening the app?*

The answer is yes. **Second Brain** is an end-to-end system where you describe a task in plain English — "remind me to call my accountant this week, medium priority" — and the AI extracts the structure (name, deadline, priority, category), then writes it directly into a Notion database. No forms. No manual tagging. Just conversation.

This was built in three layers, each exploring a different paradigm for connecting AI to external tools.

---

## Screenshots

### ChatGPT Custom GPT — Live in action
> Typing natural language tasks directly into the Custom GPT. All four tasks (including a comment) were captured and saved in a single message.

<img width="1431" height="907" alt="image" src="https://github.com/user-attachments/assets/423cb7a3-3bae-4bf5-ad62-fad2560536a5" />


### Notion Database — Auto-populated by the agent
> Tasks appear in Notion with correct deadlines, priorities, categories, and emoji icons — all inferred from unstructured text.

<img width="1431" height="907" alt="image" src="https://github.com/user-attachments/assets/21d233b1-0a5e-4cf2-8142-2b43aa3b24c4" />


### Render Deployment — Live production server
> The FastAPI backend deployed on Render, serving the ChatGPT Action endpoints publicly over HTTPS.

<img width="1431" height="907" alt="image" src="https://github.com/user-attachments/assets/ecc29b40-3b0a-42f9-a169-77e3dcbe0f1a" />


---

## The Experiment: Three Layers

### Layer 1 — Local CLI Agent (OpenAI SDK + Tool Calling)
The first version ran entirely locally. A Python script used the **OpenAI Python SDK** with **function/tool calling** to create an agent loop:

1. User types a message in the terminal
2. The message is sent to `gpt-4o-mini` with a tool schema attached
3. The model decides to call `add_to_notion_task` and returns structured JSON
4. The Python code executes the Notion API call
5. The model receives the result and confirms to the user

This is the classic "ReAct" pattern — the model reasons, acts, observes, and responds. A **FastAPI** server ran in a background thread simultaneously, exposing a `/tasks` endpoint that a **React dashboard** polled every 3 seconds to show a live log of captured tasks.

**What I learned:** Tool calling is remarkably good at extracting structure from messy language. "Book dentist next Monday, urgent" reliably becomes `{task_name: "Book dentist appointment", deadline: "2026-05-11", priority: "High", category: "Personal"}` — but only when you feed the model the current date and day of the week explicitly. LLMs are poor at calendar arithmetic without anchoring.

---

### Layer 2 — ChatGPT Custom GPT + Actions (Deployed API)
The second version decoupled the LLM from the server entirely. Instead of running OpenAI API calls locally, a **Custom GPT** in ChatGPT was given a deployed REST API to call.

Architecture:
- **FastAPI** (`chatgpt_app.py`) exposes two clean endpoints: `POST /add-task` and `POST /add-comment`
- **FastAPI auto-generates an OpenAPI 3.1 spec** at `/openapi.json`
- The Custom GPT reads this spec and learns what endpoints exist, what parameters they take, and when to call them
- When you type in ChatGPT, the GPT decides which endpoint to call and sends a structured HTTP request to the deployed server
- The server calls the Notion API and returns a confirmation

The server was deployed to **Render** (free tier) from a GitHub repo with a `render.yaml` config. No OpenAI API key is needed on the server — ChatGPT is the LLM.

**What I learned:** Custom GPT Actions are powerful but fragile to set up. The OpenAPI spec must explicitly declare a `servers` URL (FastAPI omits this by default), authentication must be declared even if `none`, and the import-from-URL feature is unreliable — pasting the schema manually is more robust.

---

### Layer 3 — MCP Server (Model Context Protocol)
The third version implements the same Notion tools as an **MCP server** using Anthropic's open [Model Context Protocol](https://modelcontextprotocol.io). MCP is the emerging standard for connecting AI models to external tools — it's to AI what USB is to hardware.

The MCP server (`mcp_server.py`) exposes the same two tools (`add_to_notion_task`, `add_comment_to_notion_task`) but in a protocol-agnostic way. Any MCP-compatible client — Claude Desktop today, and increasingly other models — can discover and call these tools without any custom integration code.

**What I learned:** MCP is significantly simpler to implement than a REST API for tool use. You write a Python function, decorate it with `@mcp.tool()`, and the protocol handles discovery, schema generation, and invocation. No HTTP routing, no request models, no OpenAPI spec.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM (local) | OpenAI `gpt-4o-mini` via Python SDK | Tool calling, date extraction, task inference |
| LLM (deployed) | ChatGPT Custom GPT | Conversational interface + Action dispatch |
| API Framework | FastAPI + Uvicorn | REST endpoints for ChatGPT Actions and React dashboard |
| Notion Integration | `notion-client` v3 (Python) | Writing tasks and comments to Notion database |
| MCP Server | `mcp[cli]` Python SDK | Protocol-native tool exposure for Claude and future models |
| Frontend | React (Create React App) | Live dashboard — connection status + task log |
| Deployment | Render (free tier) | Public HTTPS endpoint for ChatGPT Actions |
| Version Control | GitHub (`AncyJoseph01/TO-DO-OpenAI-APP`) | `main` (local CLI) + `openAI-app` (ChatGPT + MCP) |

---

## Project Structure

```
second-brain-openAI-app/
├── backend/
│   ├── notion_integration.py   ← Shared Notion API module (used by all layers)
│   ├── second_brain_server.py  ← Layer 1: Local CLI agent + FastAPI dashboard bridge
│   ├── chatgpt_app.py          ← Layer 2: Deployed FastAPI server for ChatGPT Actions
│   ├── mcp_server.py           ← Layer 3: MCP server for Claude Desktop
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.js              ← React dashboard (connection status + live task log)
│       └── App.css
├── render.yaml                 ← Render deployment config
└── README.md
```

---

## Notion Database Schema

| Property | Type | Values |
|----------|------|--------|
| Name | Title | Task name (with emoji icon inferred from category) |
| Deadline | Date | YYYY-MM-DD — resolved from relative dates by the LLM |
| Priority | Select | Low / Medium / High |
| Category | Select | Work / Personal / Other |
| Status | Status | Defaults to "Not started" |

---

## Key Engineering Decisions & Gotchas

**Date resolution needs an anchor.** Passing just `today's date` wasn't enough — the model miscalculated day-of-week. Passing `"Today is Tuesday, 2026-05-05"` fixed it.

**notion-client v3 removed `databases.query`.** The standard method for searching a database was removed in v3. Replaced with `client.search()` + filtering results by `parent.database_id`.

**FastAPI omits the `servers` field from OpenAPI by default.** ChatGPT Actions require it. Fixed by passing `servers=[{"url": "..."}]` to the `FastAPI()` constructor.

**Tool call message ordering matters.** In the OpenAI API, an assistant message with `tool_calls` must be appended to the message list *before* any tool response messages. Getting this order wrong causes a `400 BadRequest`.

**MCP vs REST for tool use.** MCP requires roughly 60% less code than a FastAPI endpoint for the same tool. The tradeoff is ecosystem maturity — REST works everywhere today; MCP works with Claude Desktop today and is expanding.

---

## Running Locally

**Backend (CLI agent):**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
python second_brain_server.py
```

**Frontend (React dashboard):**
```bash
cd frontend
npm install && npm start
# opens at http://localhost:3000
```

**MCP server (Claude Desktop):**
```bash
cd backend
source venv/bin/activate
python mcp_server.py
```
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["/absolute/path/to/backend/mcp_server.py"]
    }
  }
}
```

---

## Live Deployment

| Service | URL |
|---------|-----|
| FastAPI (Render) | https://to-do-openai-app.onrender.com |
| API Docs (Swagger) | https://to-do-openai-app.onrender.com/docs |
| OpenAPI Spec | https://to-do-openai-app.onrender.com/openapi.json |

> Note: Free Render instances spin down after 15 minutes of inactivity. The first request after idle may take ~50 seconds to wake up.

---

## What's Next

- [ ] Add a `list_tasks` tool so the GPT can read back what's in Notion
- [ ] Webhook from Notion → push notifications when a task is marked done
- [ ] Share the Custom GPT publicly
- [ ] Add OAuth so others can connect their own Notion workspace
