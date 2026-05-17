"""
pending_requests.py
-------------------
Ye module ek in-memory store hai jisme owner ke approve/reject karne se pehle
saare pending commands store hote hain.

Structure:
  pending_requests = {
      "unique_request_id": {
          "chat_id": int,          # Group chat ID jahan command aayi
          "chat_title": str,       # Group ka naam
          "from_user_id": int,     # Admin ka user ID jisne command send ki
          "from_user_name": str,   # Admin ka naam
          "command": str,          # Original command (e.g. "/ban")
          "full_text": str,        # Poora message text
          "message_id": int,       # Original message ID (already deleted)
          "reply_to_message": dict or None,  # Agar command kisi pe reply thi
          "timestamp": float,      # Time.time() — timeout ke liye
          "bot_message_id": int,   # Owner ko bheja gaya approval message ID
      }
  }
"""

import time
from typing import Optional

# Main store
pending_requests: dict = {}

# Counter for unique IDs
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
        "bot_message_id": None,  # baad mein set hoga
    }
    return request_id


def get_request(request_id: str) -> Optional[dict]:
    """Request ID se request data lo."""
    return pending_requests.get(request_id)


def set_bot_message_id(request_id: str, bot_message_id: int):
    """Owner ko bheje gaye message ki ID store karo."""
    if request_id in pending_requests:
        pending_requests[request_id]["bot_message_id"] = bot_message_id


def remove_request(request_id: str):
    """Request ko store se hata do (approve/reject/timeout ke baad)."""
    pending_requests.pop(request_id, None)


def cleanup_expired(timeout_seconds: int = 300):
    """
    Purane expired requests remove karo.
    Ye regularly call hona chahiye (job_queue via APScheduler).
    """
    now = time.time()
    expired = [
        rid
        for rid, data in pending_requests.items()
        if (now - data["timestamp"]) > timeout_seconds
    ]
    for rid in expired:
        pending_requests.pop(rid, None)
    return len(expired)
