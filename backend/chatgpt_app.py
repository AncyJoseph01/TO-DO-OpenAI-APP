"""
ChatGPT Custom GPT backend.

Exposes two endpoints that ChatGPT Actions will call directly.
No OpenAI SDK needed here — ChatGPT is the LLM; this server just
receives structured data and writes it to Notion.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from notion_integration import add_task_to_notion, add_comment_to_notion_task

load_dotenv()

app = FastAPI(
    title="Second Brain — Notion Task Agent",
    description="Saves tasks and comments to a Notion database via ChatGPT Actions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ChatGPT calls from various origins
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ────────────────────────────────────────────────────────────

class AddTaskRequest(BaseModel):
    task_name: str
    deadline: Optional[str] = None          # YYYY-MM-DD
    priority: Optional[str] = "Low"         # Low | Medium | High
    category: Optional[str] = "Other"       # Work | Personal | Other


class AddCommentRequest(BaseModel):
    task_name: str
    comment: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {"status": "Second Brain API is running"}


@app.post("/add-task")
def add_task(req: AddTaskRequest):
    """Save a new task to the Notion database."""
    result = add_task_to_notion(
        task_name=req.task_name,
        deadline=req.deadline,
        priority=req.priority,
        category=req.category,
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {
        "message": f"Task '{req.task_name}' saved to Notion.",
        "notion_url": result.get("url"),
    }


@app.post("/add-comment")
def add_comment(req: AddCommentRequest):
    """Add a comment to an existing task in the Notion database."""
    result = add_comment_to_notion_task(
        task_name=req.task_name,
        comment=req.comment,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {
        "message": f"Comment added to '{req.task_name}'.",
        "notion_url": result.get("url"),
    }
