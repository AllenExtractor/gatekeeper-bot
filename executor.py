"""
executor.py
-----------
Jab owner Yes kare tab ye module actual command execute karta hai group mein.

Bot sirf wahi commands execute kar sakta hai jo Telegram Bot API support karta hai.
Ye module har command ke liye sahi API call karta hai.
"""

import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError, BadRequest

logger = logging.getLogger(__name__)


async def execute_approved_command(bot: Bot, data: dict) -> tuple[bool, str]:
    """
    Approved command ko group mein execute karo.

    Returns:
        (success: bool, message: str)
    """
    chat_id = data["chat_id"]
    command = data["command"].lower().split()[0]  # sirf command word, args nahi
    full_text = data["full_text"]
    reply_to = data.get("reply_to_message")
    from_user_id = data["from_user_id"]

    # Command se target user ID nikalo (reply se ya args se)
    target_user_id = None
    target_username = None
    args = full_text.strip().split()[1:]  # command ke baad ke words

    if reply_to:
        target_user_id = reply_to.get("from_user_id")
        target_username = reply_to.get("from_user_name", "User")

    elif args:
        first_arg = args[0]
        if first_arg.startswith("@"):
            target_username = first_arg[1:]
        elif first_arg.lstrip("-").isdigit():
            target_user_id = int(first_arg)

    try:
        # ---- /ban ----
        if command in ("/ban", "ban"):
            if not target_user_id and not target_username:
                return False, "❌ Ban ke liye target user nahi mila"
            kwargs = {"chat_id": chat_id}
            if target_user_id:
                kwargs["user_id"] = target_user_id
            else:
                # Username se member info lo
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                kwargs["user_id"] = member.user.id

            await bot.ban_chat_member(**kwargs)
            name = target_username or str(target_user_id)
            return True, f"🔨 `{name}` ko ban kar diya gaya"

        # ---- /unban ----
        elif command in ("/unban", "unban"):
            if not target_user_id and not target_username:
                return False, "❌ Unban ke liye target user nahi mila"
            kwargs = {"chat_id": chat_id}
            if target_user_id:
                kwargs["user_id"] = target_user_id
            else:
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                kwargs["user_id"] = member.user.id

            await bot.unban_chat_member(**kwargs, only_if_banned=True)
            name = target_username or str(target_user_id)
            return True, f"✅ `{name}` ko unban kar diya gaya"

        # ---- /mute ----
        elif command in ("/mute", "mute"):
            if not target_user_id and not target_username:
                return False, "❌ Mute ke liye target user nahi mila"
            from telegram import ChatPermissions

            kwargs = {"chat_id": chat_id, "permissions": ChatPermissions(can_send_messages=False)}
            if target_user_id:
                kwargs["user_id"] = target_user_id
            else:
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                kwargs["user_id"] = member.user.id

            await bot.restrict_chat_member(**kwargs)
            name = target_username or str(target_user_id)
            return True, f"🔇 `{name}` ko mute kar diya gaya"

        # ---- /unmute ----
        elif command in ("/unmute", "unmute"):
            if not target_user_id and not target_username:
                return False, "❌ Unmute ke liye target user nahi mila"
            from telegram import ChatPermissions

            kwargs = {
                "chat_id": chat_id,
                "permissions": ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            }
            if target_user_id:
                kwargs["user_id"] = target_user_id
            else:
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                kwargs["user_id"] = member.user.id

            await bot.restrict_chat_member(**kwargs)
            name = target_username or str(target_user_id)
            return True, f"🔊 `{name}` ko unmute kar diya gaya"

        # ---- /kick ----
        elif command in ("/kick", "kick"):
            if not target_user_id and not target_username:
                return False, "❌ Kick ke liye target user nahi mila"
            
            if target_user_id:
                uid = target_user_id
            else:
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                uid = member.user.id

            # Kick = ban then unban
            await bot.ban_chat_member(chat_id=chat_id, user_id=uid)
            await bot.unban_chat_member(chat_id=chat_id, user_id=uid, only_if_banned=True)
            name = target_username or str(target_user_id)
            return True, f"👟 `{name}` ko kick kar diya gaya"

        # ---- /purge ----
        elif command in ("/purge", "purge"):
            # Purge karne ke liye hamen message ID chahiye jo reply mein ho
            if not reply_to:
                return False, "❌ Purge ke liye kisi message pe reply karni hoti hai"

            start_msg_id = reply_to.get("message_id")
            end_msg_id = data["message_id"]

            if not start_msg_id:
                return False, "❌ Start message ID nahi mili"

            deleted = 0
            failed = 0
            for msg_id in range(start_msg_id, end_msg_id + 1):
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted += 1
                except TelegramError:
                    failed += 1

            return True, f"🗑️ `{deleted}` messages delete kar diye (failed: {failed})"

        # ---- /pin ----
        elif command in ("/pin", "pin"):
            if not reply_to:
                return False, "❌ Pin ke liye kisi message pe reply karo"
            msg_id = reply_to.get("message_id")
            await bot.pin_chat_message(chat_id=chat_id, message_id=msg_id)
            return True, f"📌 Message pin kar diya gaya"

        # ---- /unpin ----
        elif command in ("/unpin", "unpin"):
            await bot.unpin_chat_message(chat_id=chat_id)
            return True, f"📌 Message unpin kar diya gaya"

        # ---- /promote ----
        elif command in ("/promote", "promote"):
            if not target_user_id and not target_username:
                return False, "❌ Promote ke liye target user nahi mila"

            if target_user_id:
                uid = target_user_id
            else:
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                uid = member.user.id

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
            name = target_username or str(target_user_id)
            return True, f"⭐ `{name}` ko promote kar diya gaya"

        # ---- /demote ----
        elif command in ("/demote", "demote"):
            if not target_user_id and not target_username:
                return False, "❌ Demote ke liye target user nahi mila"

            if target_user_id:
                uid = target_user_id
            else:
                member = await bot.get_chat_member(chat_id, f"@{target_username}")
                uid = member.user.id

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
            name = target_username or str(target_user_id)
            return True, f"⬇️ `{name}` ko demote kar diya gaya"

        # ---- /warn ----
        elif command in ("/warn", "warn"):
            reason = " ".join(args[1:]) if (target_user_id or target_username) and len(args) > 1 else " ".join(args)
            name = target_username or str(target_user_id) or "User"
            warn_text = f"⚠️ *Warning* to [{name}](tg://user?id={target_user_id or 0})"
            if reason:
                warn_text += f"\n📋 *Reason:* {reason}"
            await bot.send_message(chat_id=chat_id, text=warn_text, parse_mode="Markdown")
            return True, f"⚠️ `{name}` ko warn kar diya gaya"

        # ---- /start / /help (group mein) ----
        elif command in ("/start", "start", "/help", "help"):
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "👋 *GateKeeper Bot Active Hai!*\n\n"
                    "Main is group ki har `/command` detect karta hoon\n"
                    "aur owner se approve karwata hoon pehle.\n\n"
                    "🔒 Koi bhi admin command seedha execute nahi ho sakti!"
                ),
                parse_mode="Markdown",
            )
            return True, f"ℹ️ Help/Start message bhej diya"

        # ---- Unknown / Other commands ----
        else:
            # Generic: sirf ek confirmation message bhejo group mein
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ *Owner ne approve kiya*\n"
                    f"Command: `{full_text}`\n"
                    f"⚙️ Is command ka direct execution bot se possible nahi,\n"
                    f"lekin owner ne permission de di hai."
                ),
                parse_mode="Markdown",
            )
            return True, f"✅ Command `{command}` approved notification bhej di"

    except BadRequest as e:
        logger.error(f"BadRequest executing {command}: {e}")
        return False, f"❌ Telegram error: {e.message}"
    except TelegramError as e:
        logger.error(f"TelegramError executing {command}: {e}")
        return False, f"❌ Error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error executing {command}: {e}", exc_info=True)
        return False, f"❌ Unexpected error: {str(e)}"
