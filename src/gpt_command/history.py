from datetime import datetime
from typing import Any, Dict, List

from .config import HISTORY_FILE, load_json_file, save_json_file

MAX_HISTORY = 50


def load_history() -> List[Dict[str, Any]]:
    data = load_json_file(HISTORY_FILE, default={"items": []})
    items = data.get("items", [])
    if isinstance(items, list):
        return items
    return []


def save_history_item(
    question: str,
    command: str,
    executed: bool = False,
    copied: bool = False,
    explained: bool = False,
) -> None:
    items = load_history()
    items.insert(
        0,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "question": question,
            "command": command,
            "executed": executed,
            "copied": copied,
            "explained": explained,
        },
    )
    items = items[:MAX_HISTORY]
    save_json_file(HISTORY_FILE, {"items": items})


def print_history(limit: int = 10) -> None:
    items = load_history()[:limit]
    if not items:
        print("히스토리가 없습니다.")
        return

    for i, item in enumerate(items, start=1):
        ts = item.get("timestamp", "-")
        q = item.get("question", "")
        cmd = item.get("command", "")
        print(f"[{i}] {ts}")
        print(f"  질문: {q}")
        print(f"  명령: {cmd}")
        print()