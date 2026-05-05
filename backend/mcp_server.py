"""
MCP (Model Context Protocol) server for Second Brain.

Exposes two tools that any MCP-compatible client (Claude Desktop,
future OpenAI support, etc.) can discover and call:
  - add_to_notion_task
  - add_comment_to_notion_task

Run with:
    python mcp_server.py

Then register in Claude Desktop's config (see README).
"""

from mcp.server.fastmcp import FastMCP
from notion_integration import (
    add_task_to_notion,
    add_comment_to_notion_task as _notion_add_comment,
)

mcp = FastMCP("Second Brain")


@mcp.tool()
def add_to_notion_task(
    task_name: str,
    priority: str = "Low",
    category: str = "Other",
    deadline: str = None,
) -> str:
    """
    Save a task to the Notion Second Brain database.

    Args:
        task_name: The name of the task to save.
        priority:  Priority level — Low, Medium, or High.
        category:  Category — Work, Personal, or Other.
        deadline:  Optional deadline in YYYY-MM-DD format.
    """
    result = add_task_to_notion(
        task_name=task_name,
        priority=priority,
        category=category,
        deadline=deadline,
    )
    if "error" in result:
        return f"Error saving task: {result['error']}"
    return f"Task '{task_name}' saved to Notion. View it at: {result['url']}"


@mcp.tool()
def add_comment_to_notion_task(
    task_name: str,
    comment: str,
) -> str:
    """
    Add a comment to an existing task in the Notion database.

    Args:
        task_name: The name (or partial name) of the existing task.
        comment:   The comment or note to add.
    """
    result = _notion_add_comment(
        task_name=task_name,
        comment=comment,
    )
    if "error" in result:
        return f"Error adding comment: {result['error']}"
    return f"Comment added to '{task_name}'. View it at: {result['url']}"


if __name__ == "__main__":
    mcp.run()
