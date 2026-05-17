"""
helpers.py
----------
Reusable utility functions.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_approval_keyboard(request_id: str) -> InlineKeyboardMarkup:
    """Owner ke liye Yes/No inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes — Allow", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton("❌ No — Block", callback_data=f"reject:{request_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_approval_message(data: dict) -> str:
    """Owner ko bheja jaane wala approval message."""
    reply_info = ""
    if data.get("reply_to_message"):
        rt = data["reply_to_message"]
        reply_user = rt.get("from_user_name", "Unknown")
        reply_text = rt.get("text") or "[media/sticker]"
        if len(reply_text) > 100:
            reply_text = reply_text[:100] + "…"
        reply_info = f"\n↩️ *Reply to:* `{reply_user}` — {reply_text}"

    # Delete status
    deleted = data.get("delete_success", True)
    delete_status = "✅ Message deleted" if deleted else "⚠️ Delete failed (check bot permissions)"

    msg = (
        f"👋 *Hey Boss!*\n"
        f"Please classify this request:\n\n"
        f"👤 *Admin:* [{data['from_user_name']}](tg://user?id={data['from_user_id']})\n"
        f"🏠 *Group:* `{data['chat_title']}`\n"
        f"📝 *Command:* `{data['full_text']}`"
        f"{reply_info}\n\n"
        f"🗑️ {delete_status}\n\n"
        f"_Allow karna hai ya block?_"
    )
    return msg


def format_approved_message(data: dict) -> str:
    return (
        f"✅ *Approved!*\n"
        f"Command `{data['command']}` execute ho raha hai\n"
        f"Group: `{data['chat_title']}`"
    )


def format_rejected_message(data: dict) -> str:
    return (
        f"❌ *Rejected!*\n"
        f"Command `{data['command']}` block kar diya\n"
        f"Group: `{data['chat_title']}`"
    )


def format_timeout_message(data: dict) -> str:
    return (
        f"⏰ *Timeout!*\n"
        f"Command `{data['command']}` expire ho gayi\n"
        f"Group: `{data['chat_title']}`"
    )
