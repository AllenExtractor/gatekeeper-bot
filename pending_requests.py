"""
pending_requests.py
-------------------
File-based persistent store for pending commands awaiting owner approval.
Restart hone pe bhi requests SAFE rahenge — JSON file mein save hote hain.
"""

import json
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Persistence file path
_STORE_FILE = "pending_requests_store.json"

# In-memory cache
pending_requests: dict = {}
_counter = 0


def _load_from_disk():
    """Startup pe disk se load karo."""
    global pending_requests, _counter
    if os.path.exists(_STORE_FILE):
        try:
            with open(_STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            pending_requests = data.get("requests", {})
            _counter = data.get("counter", 0)
            logger.info(f"[STORE] ✅ Loaded {len(pending_requests)} requests from disk")
        except Exception as e:
            logger.warning(f"[STORE] Load failed, starting fresh: {e}")
            pending_requests = {}
            _counter = 0
    else:
        pending_requests = {}
        _counter = 0


def _save_to_disk():
    """Har change ke baad disk pe save karo."""
    try:
        with open(_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"requests": pending_requests, "counter": _counter},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        logger.warning(f"[STORE] Save failed: {e}")


# Startup pe load karo
_load_from_disk()


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
        "delete_success": delete_success,
    }

    _save_to_disk()  # Turant disk pe save
    return request_id


def get_request(request_id: str) -> Optional[dict]:
    return pending_requests.get(request_id)


def set_bot_message_id(request_id: str, bot_message_id: int):
    if request_id in pending_requests:
        pending_requests[request_id]["bot_message_id"] = bot_message_id
        _save_to_disk()


def remove_request(request_id: str):
    pending_requests.pop(request_id, None)
    _save_to_disk()


def cleanup_expired(timeout_seconds: int = 300) -> int:
    now = time.time()
    expired = [
        rid
        for rid, data in list(pending_requests.items())
        if (now - data["timestamp"]) > timeout_seconds
    ]
    for rid in expired:
        pending_requests.pop(rid, None)
    if expired:
        _save_to_disk()
    return len(expired)
