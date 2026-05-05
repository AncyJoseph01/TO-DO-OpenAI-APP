import os
from dotenv import load_dotenv
from notion_client import Client, APIResponseError

load_dotenv()

_client = Client(auth=os.environ["NOTION_INTEGRATION_SECRET"])
_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

# Change to "Not started" if your Status property uses Notion's built-in Status type
_DEFAULT_STATUS = "Not started"


def add_task_to_notion(
    task_name: str,
    priority: str = "Low",
    category: str = "Other",
    deadline: str = None,
) -> dict:
    properties = {
        "Name": {
            "title": [{"text": {"content": task_name}}]
        },
        "Priority": {
            "select": {"name": priority}
        },
        "Category": {
            "select": {"name": category}
        },
    }

    if deadline:
        properties["Deadline"] = {"date": {"start": deadline}}

    # Try Notion Status property type first; fall back to Checkbox if unsupported
    try:
        properties["Status"] = {"status": {"name": _DEFAULT_STATUS}}
        page = _client.pages.create(
            parent={"database_id": _DATABASE_ID},
            properties=properties,
        )
    except APIResponseError:
        # Database uses a Checkbox property instead of Status
        properties["Status"] = {"checkbox": False}
        page = _client.pages.create(
            parent={"database_id": _DATABASE_ID},
            properties=properties,
        )

    return {
        "id": page["id"],
        "url": page["url"],
        "task_name": task_name,
        "deadline": deadline,
        "priority": priority,
        "category": category,
    }


def add_comment_to_notion_task(task_name: str, comment: str) -> dict:
    # databases.query was removed in notion-client 3.x; use search instead
    results = _client.search(
        query=task_name,
        filter={"value": "page", "property": "object"},
    )

    # Normalise both IDs to no-dash format for comparison
    db_id_plain = _DATABASE_ID.replace("-", "")
    pages = [
        r for r in results.get("results", [])
        if r.get("parent", {}).get("database_id", "").replace("-", "") == db_id_plain
    ]

    if not pages:
        return {"error": f"No task found matching '{task_name}'"}

    page = pages[0]

    _client.comments.create(
        parent={"page_id": page["id"]},
        rich_text=[{"text": {"content": comment}}],
    )

    return {
        "success": True,
        "task_name": task_name,
        "comment": comment,
        "url": page["url"],
    }
