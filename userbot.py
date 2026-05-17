"""
userbot.py — GateKeeper Userbot (Pyrogram MTProto)
===================================================

YE USERBOT HAI — Real Telegram account se chalta hai.
Isliye ye commands ko TRULY intercept kar sakta hai
kisi bhi bot (MissRose etc.) se PEHLE.

FLOW:
1. Group mein admin /command bhejta hai
2. Userbot MTProto level pe message SEEDHA receive karta hai
   (Telegram server pe — Bot API se pehle)
3. Userbot turant message DELETE karta hai
4. GatekeeperBot (Bot API) ko signal deta hai owner ko PM bhejne ke liye
5. Owner YES → execute | Owner NO → block

IMPORTANT:
- Ye tumhara real Telegram account use karta hai
- config.py mein STRING_SESSION paste karo
- Account safe rakhne ke liye sirf groups mein use karo
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    MessageDeleteForbidden,
    ChatAdminRequired,
    UserNotParticipant,
    FloodWait,
    RPCError,
)

import config

logger = logging.getLogger(__name__)

# ── Pyrogram Client (Userbot) ────────────────────────────────────────────────
userbot = Client(
    name="gatekeeper_userbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.STRING_SESSION,
)

# ── Reference to main bot application (set karo main.py mein) ───────────────
_bot_app = None  # telegram.ext.Application

def set_bot_app(app):
    """Main bot ka reference yahan store karo."""
    global _bot_app
    _bot_app = app


# ── Owner ID shortcut ─────────────────────────────────────────────────────────
OWNER_ID = config.OWNER_ID


# ═══════════════════════════════════════════════════════════════════════════════
#   ADMIN CHECK HELPER
# ═══════════════════════════════════════════════════════════════════════════════

async def user_is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check karo ki user is group ka admin hai ya nahi."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status.value in ("administrator", "creator")
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#   CORE INTERCEPTOR — MTProto Level (Sabse pehle chalta hai)
# ═══════════════════════════════════════════════════════════════════════════════

@userbot.on_message(
    filters.command(
        # Ye saari commands intercept hongi
        [
            "ban", "unban", "mute", "unmute", "kick", "purge",
            "pin", "unpin", "unpinall", "promote", "demote",
            "warn", "del", "delete", "tban", "tmute", "kick",
            "kickme", "warn", "rmwarn", "warns", "clearwarn",
            "report", "filter", "stop", "filters", "start", "help",
        ]
    )
    & (filters.group | filters.supergroup)
    & ~filters.me  # Apne messages intercept mat karo
)
async def intercept_any_command(client: Client, message: Message):
    """
    MTProto level pe command intercept karo.
    Ye Bot API se PEHLE chalta hai — isliye MissRose ko message milne se PEHLE
    hum delete kar sakte hain.
    """
    user = message.from_user
    chat = message.chat

    if not user:
        return

    # Owner ki commands seedhi pass karo
    if user.id == OWNER_ID:
        logger.info(f"Owner command — pass through: {message.text}")
        return

    # Admin check — sirf admin ki commands intercept karo
    admin = await user_is_admin(client, chat.id, user.id)
    if not admin:
        # Non-admin ne command try ki — delete karo silently
        try:
            await message.delete()
        except Exception:
            pass
        return

    command_text = message.text or message.caption or ""
    if not command_text.startswith("/"):
        return

    logger.info(f"[USERBOT] Intercepted: '{command_text}' from {user.first_name} in '{chat.title}'")

    # ── STEP 1: TURANT DELETE — Bot API se PEHLE ────────────────────────────
    deleted = False
    try:
        await message.delete()
        deleted = True
        logger.info(f"[USERBOT] ✅ Message {message.id} deleted BEFORE any bot saw it")
    except (MessageDeleteForbidden, ChatAdminRequired) as e:
        logger.warning(f"[USERBOT] ⚠️ Could not delete: {e}")
    except FloodWait as e:
        logger.warning(f"[USERBOT] FloodWait {e.value}s")
        await asyncio.sleep(e.value)
        try:
            await message.delete()
            deleted = True
        except Exception:
            pass
    except RPCError as e:
        logger.warning(f"[USERBOT] RPCError on delete: {e}")

    # ── STEP 2: Reply-to info collect karo ──────────────────────────────────
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

    # ── STEP 3: Main bot ko signal karo — owner se approval lo ──────────────
    # _bot_app ke through Bot API bot ko trigger karo
    if _bot_app:
        try:
            await _bot_app.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"👋 *Hey Boss!*\n"
                    f"Please classify this request:\n\n"
                    f"👤 *Admin:* [{user.first_name}](tg://user?id={user.id})\n"
                    f"🏠 *Group:* `{chat.title}`\n"
                    f"📝 *Command:* `{command_text}`\n"
                    f"🗑️ {'✅ Message deleted (MissRose nahi dekhegi)' if deleted else '⚠️ Delete failed'}\n\n"
                    f"_Allow karna hai ya block?_"
                ),
                parse_mode="markdown",
                reply_markup=_build_keyboard_data(
                    chat_id=chat.id,
                    chat_title=chat.title or "Unknown",
                    from_user_id=user.id,
                    from_user_name=user.first_name,
                    command_text=command_text,
                    message_id=message.id,
                    reply_data=reply_data,
                    deleted=deleted,
                ),
            )
        except Exception as e:
            logger.error(f"[USERBOT] Failed to notify owner via bot: {e}")
    else:
        logger.error("[USERBOT] _bot_app not set! Cannot notify owner.")


def _build_keyboard_data(
    chat_id, chat_title, from_user_id, from_user_name,
    command_text, message_id, reply_data, deleted
):
    """
    Inline keyboard banao aur request store mein save karo.
    Import yahan karo taaki circular import na ho.
    """
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
    """Userbot start karo."""
    await userbot.start()
    me = await userbot.get_me()
    logger.info(f"[USERBOT] ✅ Started as: {me.first_name} (@{me.username}) | ID: {me.id}")


async def stop_userbot():
    """Userbot stop karo."""
    await userbot.stop()
    logger.info("[USERBOT] Stopped.")
