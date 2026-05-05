import json
import os
import threading
from collections import deque
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import uvicorn

from notion_integration import add_task_to_notion, add_comment_to_notion_task

load_dotenv()

app = FastAPI(title="Second Brain API")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

task_log: deque = deque(maxlen=5)
task_log_lock = threading.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API endpoints for the React dashboard ────────────────────────────────────

@app.get("/status")
def status():
    return {"status": "connected", "timestamp": datetime.now().isoformat()}


@app.get("/tasks")
def get_tasks():
    with task_log_lock:
        return {"tasks": list(task_log)}


# ── OpenAI tool schema ────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_to_notion_task",
            "description": (
                "Save a task to the user's Notion Second Brain database. "
                "Call this whenever the user mentions something they need to do, "
                "remember, complete, or any action item — even if described informally."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_name": {
                        "type": "string",
                        "description": (
                            "The name/title of the task. Extract the core action item "
                            "from the user's message in plain, imperative language."
                        ),
                    },
                    "deadline": {
                        "type": "string",
                        "description": (
                            "Deadline in YYYY-MM-DD format. Convert relative dates "
                            "(e.g., 'tomorrow', 'next Friday', 'end of month') to "
                            "absolute dates. Omit entirely if no deadline is mentioned."
                        ),
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High"],
                        "description": (
                            "Priority level. 'High' for urgent/ASAP/critical tasks, "
                            "'Medium' for tasks with a near deadline or importance, "
                            "'Low' for everything else."
                        ),
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Work", "Personal", "Other"],
                        "description": (
                            "'Work' for job/meeting/project/client tasks, "
                            "'Personal' for health/family/home/errands, "
                            "'Other' when the category is unclear."
                        ),
                    },
                },
                "required": ["task_name", "priority", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_comment_to_notion_task",
            "description": (
                "Add a comment or note to an existing task in the Notion database. "
                "Use this when the user wants to annotate, update, or add a reminder "
                "to a task that already exists."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_name": {
                        "type": "string",
                        "description": "The name (or partial name) of the existing task to comment on.",
                    },
                    "comment": {
                        "type": "string",
                        "description": "The comment or note to add to the task.",
                    },
                },
                "required": ["task_name", "comment"],
            },
        },
    },
]

def _system_prompt() -> str:
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    weekday = now.strftime("%A")  # e.g. "Tuesday"
    return (
        f"You are Second Brain, an intelligent task-capture assistant. "
        f"Today is {weekday}, {today}. "
        "Whenever the user describes a task, todo, reminder, or action item, "
        "you must call add_to_notion_task to save it to their Notion database. "
        f"Resolve all relative dates (e.g. 'next Monday', 'tomorrow', 'in 2 weeks') "
        f"to absolute YYYY-MM-DD dates. Today is {weekday} {today}, so use that as your "
        "anchor — do not guess the day of the week. "
        "Infer priority and category from context. "
        "After saving, confirm with a short, friendly message."
    )


# ── Agent logic ───────────────────────────────────────────────────────────────

def run_agent(user_message: str) -> str:
    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": user_message},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    message = response.choices[0].message

    if not message.tool_calls:
        return message.content or "No task detected. Please describe something you need to do."

    # Assistant message must come before all tool responses
    messages.append(message)

    for tool_call in message.tool_calls:
        args = json.loads(tool_call.function.arguments)

        if tool_call.function.name == "add_to_notion_task":
            result = add_task_to_notion(**args)
            with task_log_lock:
                task_log.append({
                    "task_name": args.get("task_name"),
                    "deadline": args.get("deadline"),
                    "priority": args.get("priority"),
                    "category": args.get("category"),
                    "timestamp": datetime.now().isoformat(),
                    "notion_url": result.get("url"),
                })

        elif tool_call.function.name == "add_comment_to_notion_task":
            result = add_comment_to_notion_task(**args)

        else:
            result = {"error": f"Unknown tool: {tool_call.function.name}"}

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result),
        })

    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return final.choices[0].message.content


# ── CLI loop ──────────────────────────────────────────────────────────────────

def cli_loop():
    print("\n  Second Brain Agent Ready")
    print("  Describe any task — I'll save it to Notion.")
    print("  Type 'quit' to exit.\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye.")
                break
            if user_input:
                print("Agent: Saving to Notion...")
                result = run_agent(user_input)
                print(f"Agent: {result}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break


if __name__ == "__main__":
    import signal, sys

    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning"))

    def _shutdown(sig, frame):
        server.should_exit = True
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    print("  Dashboard API listening on http://localhost:8000")
    cli_loop()
    server.should_exit = True
