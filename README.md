# Second Brain — Notion Task Agent

An autonomous agent that listens for tasks via a CLI, extracts structured data using OpenAI tool calling, and saves them to your Notion database. A React dashboard shows connection status and a live log of the last 5 captured tasks.

---

## Project Structure

```
second-brain-openAI-app/
├── backend/
│   ├── .env                    ← your credentials (already configured)
│   ├── .env.example
│   ├── requirements.txt
│   ├── notion_integration.py   ← Notion API module
│   └── second_brain_server.py  ← OpenAI agent + FastAPI bridge
└── frontend/
    └── src/
        ├── App.js              ← React dashboard
        └── App.css
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- Your Notion integration has been connected to the database (see below)

### Connect your Notion integration to the database

1. Go to your Notion database page
2. Click `...` (top-right) → **Connections** → **Connect to** → select your integration
3. Without this step the API will return a 404

---

## Running the Python Agent

```bash
cd backend
source venv/bin/activate          # Windows: venv\Scripts\activate
python second_brain_server.py
```

You will see:

```
  Dashboard API listening on http://localhost:8000
  Second Brain Agent Ready
  Describe any task — I'll save it to Notion.
  Type 'quit' to exit.

You: _
```

---

## Running the React Dashboard

Open a **second terminal**:

```bash
cd frontend
npm start
```

The dashboard opens at `http://localhost:3000` and polls the agent every 3–5 seconds.

---

## Testing — Example inputs

Type any of these at the `You:` prompt:

```
Finish the Q3 report by Friday, it's urgent
Book dentist appointment next Monday
Review pull requests for the auth module — medium priority
Buy groceries this weekend
```

The agent will:
1. Call `add_to_notion_task` with extracted fields
2. Push the task to your Notion database
3. Show a confirmation message
4. The React dashboard will display the task within 3 seconds

---

## API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Returns `{"status": "connected"}` when the server is running |
| GET | `/tasks` | Returns the last 5 tasks captured in the current session |

---

## Notion Database Schema

| Property | Type | Notes |
|----------|------|-------|
| Name | Title | Task name |
| Deadline | Date | YYYY-MM-DD |
| Priority | Select | Low / Medium / High |
| Category | Select | Work / Personal / Other |
| Status | Status | Defaults to "Not started" |

---

## Regenerating API Keys

Since keys were shared during setup, regenerate them now:

- **Notion**: [notion.so/my-integrations](https://www.notion.so/my-integrations) → your integration → Regenerate secret → update `backend/.env`
- **OpenAI**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys) → delete key → create new → update `backend/.env`
