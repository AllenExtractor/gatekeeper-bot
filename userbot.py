"""
userbot.py — GateKeeper Userbot (Pyrogram MTProto)
===================================================

YE USERBOT HAI — Real Telegram account se chalta hai.
Isliye ye commands ko TRULY intercept kar sakta hai
kisi bhi bot (MissRose etc.) se PEHLE.

FLOW:
1. Group mein KISI BHI USER (admin/normal/owner) ne /command bheja
2. Userbot MTProto level pe message SEEDHA receive karta hai
3. Userbot TURANT message DELETE karta hai (bina koi check ke)
4. GatekeeperBot (Bot API) ko signal deta hai owner ko PM bhejne ke liye
5. Owner YES → execute | Owner NO → block

IMPORTANT:
- Ye tumhara real Telegram account use karta hai
- config.py mein STRING_SESSION paste karo
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    MessageDeleteForbidden,
    ChatAdminRequired,
    FloodWait,
    RPCError,
)

import config

logger = logging.getLogger(__name__)

# ── Pyrogram Client (Userbot) ─────────────────────────────────────────────────
userbot = Client(
    name="gatekeeper_userbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.STRING_SESSION,
)

# ── Reference to main bot application ────────────────────────────────────────
_bot_app = None

def set_bot_app(app):
    global _bot_app
    _bot_app = app

OWNER_ID = config.OWNER_ID

# ── Saari commands jo intercept hongi ────────────────────────────────────────
INTERCEPT_COMMANDS = [
    "ban", "unban", "mute", "unmute", "kick", "purge",
    "pin", "unpin", "unpinall", "promote", "demote",
    "warn", "lock", "unlock", "delete", "del",
    "tmute", "kickme", "rmwarn", "warns", "clearwarn",
    "report", "filter", "stop", "filters", "start", "help",
    "id", "info", "rules", "setrules", "resetrules",
    "adminlist", "title", "setgpic", "setdesc",
    "welcome", "setwelcome", "resetwelcome",
    "antiflood", "setflood", "flood",
    "blacklist", "addblacklist", "unblacklist",
    "notes", "get", "save", "clear",
    "invite", "link",
]


# ═══════════════════════════════════════════════════════════════════════════════
#   CORE INTERCEPTOR — MTProto Level
#   SABHI USERS intercept hote hain EXCEPT config.py wala real OWNER
# ═══════════════════════════════════════════════════════════════════════════════

@userbot.on_message(
    filters.command(INTERCEPT_COMMANDS) & filters.group
)
async def intercept_any_command(client: Client, message: Message):
    user = message.from_user
    chat = message.chat

    if not user:
        return

    # Sirf config.py wala REAL OWNER bypass karta hai — baaki sabka intercept
    if user.id == OWNER_ID:
        logger.info(f"[USERBOT] Owner command — pass through: {message.text}")
        return

    command_text = message.text or message.caption or ""
    if not command_text.startswith("/"):
        return

    logger.info(
        f"[USERBOT] Intercepting: '{command_text}' "
        f"from {user.first_name} (ID:{user.id}) in '{chat.title}'"
    )

    # ── STEP 1: TURANT DELETE — bina kisi check ke ───────────────────────────
    deleted = False
    try:
        await message.delete()
        deleted = True
        logger.info(f"[USERBOT] ✅ Deleted msg {message.id} BEFORE any bot saw it")
    except (MessageDeleteForbidden, ChatAdminRequired) as e:
        logger.warning(f"[USERBOT] ⚠️ Could not delete: {e}")
    except FloodWait as e:
        await asyncio.sleep(min(e.value, 3))
        try:
            await message.delete()
            deleted = True
        except Exception:
            pass
    except (RPCError, Exception) as e:
        logger.warning(f"[USERBOT] Delete error: {e}")

    # ── STEP 2: Reply-to info collect karo ───────────────────────────────────
    reply_data = None
    if message.reply_to_message:
        rto = message.reply_to_message
        rto_user = rto.from_user
        reply_data = {
            "message_id": rto.id,
            "from_user_id": rto_user.id if rto_user else None,
            "from_user_name": rto_user.first_name if rto_user else "Unknown",
            "text": rto.text or rto.caption or "",
        }

    # ── STEP 3: Owner ko DM mein TURANT notify karo ──────────────────────────
    if _bot_app:
        try:
            keyboard = _build_keyboard_data(
                chat_id=chat.id,
                chat_title=chat.title or "Unknown",
                from_user_id=user.id,
                from_user_name=user.first_name,
                command_text=command_text,
                message_id=message.id,
                reply_data=reply_data,
                deleted=deleted,
            )

            # User role check (just for info)
            try:
                member = await client.get_chat_member(chat.id, user.id)
                role_map = {
                    "administrator": "👑 Admin",
                    "creator": "🏆 Creator",
                    "member": "👤 Member",
                    "restricted": "⛔ Restricted",
                }
                user_role = role_map.get(member.status.value, "❓ Unknown")
            except Exception:
                user_role = "❓ Unknown"

            await _bot_app.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"🚨 *Command Intercepted!*\n\n"
                    f"👤 *User:* [{user.first_name}](tg://user?id={user.id})\n"
                    f"🏷️ *Role:* {user_role}\n"
                    f"🆔 *User ID:* `{user.id}`\n"
                    f"🏠 *Group:* `{chat.title}`\n"
                    f"📝 *Command:* `{command_text}`\n"
                    f"🗑️ {'✅ Deleted (Rose nahi dekhegi)' if deleted else '⚠️ Delete fail hua'}\n\n"
                    f"_Allow karna hai ya block?_"
                ),
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            logger.info(f"[USERBOT] ✅ Owner DM bheja for: {command_text}")
        except Exception as e:
            logger.error(f"[USERBOT] ❌ Owner notify FAIL: {e}", exc_info=True)
    else:
        logger.error("[USERBOT] _bot_app not set! Cannot notify owner.")


def _build_keyboard_data(
    chat_id, chat_title, from_user_id, from_user_name,
    command_text, message_id, reply_data, deleted
):
    import pending_requests as store
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    request_id = store.add_request(
        chat_id=chat_id,
        chat_title=chat_title,
        from_user_id=from_user_id,
        from_user_name=from_user_name,
        command=command_text.split()[0],
        full_text=command_text,
        message_id=message_id,
        reply_to_message=reply_data,
        delete_success=deleted,
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes — Allow", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton("❌ No — Block", callback_data=f"reject:{request_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ═══════════════════════════════════════════════════════════════════════════════
#   USERBOT START/STOP
# ═══════════════════════════════════════════════════════════════════════════════

async def start_userbot():
    await userbot.start()
    me = await userbot.get_me()
    logger.info(f"[USERBOT] ✅ Started as: {me.first_name} (@{me.username}) | ID: {me.id}")


async def stop_userbot():
    await userbot.stop()
    logger.info("[USERBOT] Stopped.")
