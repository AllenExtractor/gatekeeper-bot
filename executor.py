"""
executor.py — Command Executor
--------------------------------
Sirf tab chalta hai jab owner YES press kare.
NO press hone pe yeh kabhi nahi chalta.

MissRose compatible commands support karta hai.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from telegram import Bot, ChatPermissions
from telegram.error import TelegramError, BadRequest

logger = logging.getLogger(__name__)


async def execute_approved_command(bot: Bot, data: dict) -> tuple[bool, str]:
    """
    Owner-approved command execute karo.

    SIRF YAH TAB CALL HOTA HAI JAB OWNER NE YES DABAYA HO.
    NO pe yeh function kabhi call nahi hota.

    Returns:
        (success: bool, message: str)
    """
    chat_id = data["chat_id"]
    command = data["command"].lower().lstrip("/")
    full_text = data["full_text"]
    reply_to = data.get("reply_to_message")
    from_user_id = data["from_user_id"]

    # Args parse karo
    args = full_text.strip().split()[1:]

    # Target user ID/username nikalo
    target_user_id = None
    target_username = None

    if reply_to:
        target_user_id = reply_to.get("from_user_id")
        target_username = reply_to.get("from_user_name", "User")

    elif args:
        first_arg = args[0]
        if first_arg.startswith("@"):
            target_username = first_arg[1:]
        elif first_arg.lstrip("-").isdigit():
            target_user_id = int(first_arg)

    async def resolve_user_id() -> Optional[int]:
        """Username se user ID lo."""
        if target_user_id:
            return target_user_id
        if target_username:
            try:
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                return member.user.id
            except TelegramError:
                return None
        return None

    try:
        # ─── /ban ──────────────────────────────────────────────────────────
        if command == "ban":
            uid = await resolve_user_id()
            if not uid:
                return False, "❌ Target user nahi mila (reply karo ya @username do)"
            await bot.ban_chat_member(chat_id=chat_id, user_id=uid)
            name = target_username or str(uid)
            return True, f"🔨 `{name}` ko ban kar diya"

        # ─── /unban ────────────────────────────────────────────────────────
        elif command == "unban":
            uid = await resolve_user_id()
            if not uid:
                return False, "❌ Target user nahi mila"
            await bot.unban_chat_member(chat_id=chat_id, user_id=uid, only_if_banned=True)
            name = target_username or str(uid)
            return True, f"✅ `{name}` ko unban kar diya"

        # ─── /mute ─────────────────────────────────────────────────────────
        elif command == "mute":
            uid = await resolve_user_id()
            if not uid:
                return False, "❌ Target user nahi mila"

            # Time parse karo agar diya ho (e.g. /mute @user 1h)
            until = None
            time_arg = args[-1] if args else ""
            if time_arg and time_arg[:-1].isdigit():
                amount = int(time_arg[:-1])
                unit = time_arg[-1].lower()
                if unit == "m":
                    until = datetime.now() + timedelta(minutes=amount)
                elif unit == "h":
                    until = datetime.now() + timedelta(hours=amount)
                elif unit == "d":
                    until = datetime.now() + timedelta(days=amount)

            kwargs = {
                "chat_id": chat_id,
                "user_id": uid,
                "permissions": ChatPermissions(can_send_messages=False),
            }
            if until:
                kwargs["until_date"] = until

            await bot.restrict_chat_member(**kwargs)
            name = target_username or str(uid)
            time_str = f" for {time_arg}" if until else " permanently"
            return True, f"🔇 `{name}` ko mute kar diya{time_str}"

        # ─── /unmute ───────────────────────────────────────────────────────
        elif command == "unmute":
            uid = await resolve_user_id()
            if not uid:
                return False, "❌ Target user nahi mila"

            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=uid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            name = target_username or str(uid)
            return True, f"🔊 `{name}` ko unmute kar diya"

        # ─── /kick ─────────────────────────────────────────────────────────
        elif command == "kick":
            uid = await resolve_user_id()
            if not uid:
                return False, "❌ Target user nahi mila"
            await bot.ban_chat_member(chat_id=chat_id, user_id=uid)
            await bot.unban_chat_member(chat_id=chat_id, user_id=uid, only_if_banned=True)
            name = target_username or str(uid)
            return True, f"👟 `{name}` ko kick kar diya"

        # ─── /purge ────────────────────────────────────────────────────────
        elif command == "purge":
            if not reply_to:
                return False, "❌ Purge ke liye kisi message pe reply karo"

            start_msg_id = reply_to.get("message_id")
            end_msg_id = data["message_id"]

            if not start_msg_id:
                return False, "❌ Start message ID nahi mili"

            # Batch delete (faster)
            deleted = 0
            failed = 0
            batch = []

            for msg_id in range(start_msg_id, end_msg_id + 1):
                batch.append(msg_id)
                if len(batch) >= 100:
                    try:
                        await bot.delete_messages(chat_id=chat_id, message_ids=batch)
                        deleted += len(batch)
                    except TelegramError:
                        # Fallback: one by one
                        for mid in batch:
                            try:
                                await bot.delete_message(chat_id=chat_id, message_id=mid)
                                deleted += 1
                            except TelegramError:
                                failed += 1
                    batch = []

            # Remaining batch
            if batch:
                try:
                    await bot.delete_messages(chat_id=chat_id, message_ids=batch)
                    deleted += len(batch)
                except TelegramError:
                    for mid in batch:
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=mid)
                            deleted += 1
                        except TelegramError:
                            failed += 1

            return True, f"🗑️ `{deleted}` messages delete kiye (failed: {failed})"

        # ─── /pin ──────────────────────────────────────────────────────────
        elif command == "pin":
            if not reply_to:
                return False, "❌ Pin ke liye kisi message pe reply karo"
            msg_id = reply_to.get("message_id")
            # loud=False to avoid pin notification
            loud = "loud" in full_text.lower() or "notify" in full_text.lower()
            await bot.pin_chat_message(
                chat_id=chat_id,
                message_id=msg_id,
                disable_notification=not loud,
            )
            return True, "📌 Message pin kar diya"

        # ─── /unpin ────────────────────────────────────────────────────────
        elif command == "unpin":
            if reply_to:
                msg_id = reply_to.get("message_id")
                await bot.unpin_chat_message(chat_id=chat_id, message_id=msg_id)
            else:
                await bot.unpin_chat_message(chat_id=chat_id)
            return True, "📌 Message unpin kar diya"

        # ─── /unpinall ─────────────────────────────────────────────────────
        elif command == "unpinall":
            await bot.unpin_all_chat_messages(chat_id=chat_id)
            return True, "📌 Saare messages unpin kar diye"

        # ─── /promote ──────────────────────────────────────────────────────
        elif command == "promote":
            uid = await resolve_user_id()
            if not uid:
                return False, "❌ Target user nahi mila"

            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=uid,
                can_change_info=True,
                can_delete_messages=True,
                can_invite_users=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_manage_chat=True,
            )
            name = target_username or str(uid)
            return True, f"⭐ `{name}` ko admin promote kar diya"

        # ─── /demote ───────────────────────────────────────────────────────
        elif command == "demote":
            uid = await resolve_user_id()
            if not uid:
                return False, "❌ Target user nahi mila"

            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=uid,
                can_change_info=False,
                can_delete_messages=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_manage_chat=False,
            )
            name = target_username or str(uid)
            return True, f"⬇️ `{name}` ko demote kar diya"

        # ─── /warn ─────────────────────────────────────────────────────────
        elif command == "warn":
            uid = await resolve_user_id()
            name = target_username or (str(uid) if uid else "User")
            reason_args = args[1:] if (target_user_id or target_username) else args
            reason = " ".join(reason_args) if reason_args else "No reason given"

            warn_text = (
                f"⚠️ *Warning!*\n"
                f"User: [{name}](tg://user?id={uid or 0})\n"
                f"📋 Reason: {reason}"
            )
            await bot.send_message(chat_id=chat_id, text=warn_text, parse_mode="Markdown")
            return True, f"⚠️ `{name}` ko warn kiya"

        # ─── /del ──────────────────────────────────────────────────────────
        elif command == "del":
            if reply_to:
                msg_id = reply_to.get("message_id")
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    return True, "🗑️ Message delete kar diya"
                except TelegramError as e:
                    return False, f"❌ Delete failed: {e}"
            return False, "❌ Delete ke liye kisi message pe reply karo"

        # ─── /start / /help (group mein) ───────────────────────────────────
        elif command in ("start", "help"):
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "👋 *GateKeeper Bot Active!*\n\n"
                    "Har `/command` owner se approve hogi.\n"
                    "🔒 Koi bhi command seedha execute nahi hogi!"
                ),
                parse_mode="Markdown",
            )
            return True, "ℹ️ Info message bhej diya"

        # ─── Unknown / Other commands ───────────────────────────────────────
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ *Owner ne approve kiya*\n"
                    f"Command: `{full_text}`\n\n"
                    f"⚙️ Is command ka direct execution is bot se possible nahi,\n"
                    f"lekin owner ne permission de di hai."
                ),
                parse_mode="Markdown",
            )
            return True, f"✅ `{command}` approved notification bhej di"

    except BadRequest as e:
        logger.error(f"BadRequest executing /{command}: {e}")
        return False, f"❌ Telegram error: {e.message}"
    except TelegramError as e:
        logger.error(f"TelegramError executing /{command}: {e}")
        return False, f"❌ Error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error executing /{command}: {e}", exc_info=True)
        return False, f"❌ Unexpected error: {str(e)}"
