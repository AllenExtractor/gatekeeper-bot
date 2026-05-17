"""
pending_requests.py
-------------------
In-memory store for pending commands awaiting owner approval.
"""

import time
from typing import Optional

# Main store
pending_requests: dict = {}

_counter = 0


def add_request(
    chat_id: int,
    chat_title: str,
    from_user_id: int,
    from_user_name: str,
    command: str,
    full_text: str,
    message_id: int,
    reply_to_message: Optional[dict] = None,
    delete_success: bool = True,
) -> str:
    """Naya request store karo, unique request_id return karo."""
    global _counter
    _counter += 1
    request_id = f"req_{int(time.time())}_{_counter}"

    pending_requests[request_id] = {
        "chat_id": chat_id,
        "chat_title": chat_title,
        "from_user_id": from_user_id,
        "from_user_name": from_user_name,
        "command": command,
        "full_text": full_text,
        "message_id": message_id,
        "reply_to_message": reply_to_message,
        "timestamp": time.time(),
        "bot_message_id": None,
        "delete_success": delete_success,  # Track karo ki original message delete hua ya nahi
    }
    return request_id


def get_request(request_id: str) -> Optional[dict]:
    return pending_requests.get(request_id)


def set_bot_message_id(request_id: str, bot_message_id: int):
    if request_id in pending_requests:
        pending_requests[request_id]["bot_message_id"] = bot_message_id


def remove_request(request_id: str):
    pending_requests.pop(request_id, None)


def cleanup_expired(timeout_seconds: int = 300) -> int:
    now = time.time()
    expired = [
        rid
        for rid, data in pending_requests.items()
        if (now - data["timestamp"]) > timeout_seconds
    ]
    for rid in expired:
        pending_requests.pop(rid, None)
    return len(expired)
