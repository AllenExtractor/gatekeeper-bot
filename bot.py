"""
bot.py — GateKeeper Bot
=======================

FLOW:
1. Group mein koi admin koi bhi /command bhejta hai
2. Bot us message ko DELETE kar deta hai (taaki execute na ho directly)
3. Bot Owner ko PM mein approval message bhejta hai (Yes/No buttons ke saath)
4. Owner Yes dabaata hai → bot us command ko execute karta hai group mein
5. Owner No dabaata hai → silently ignore, admin ko notify karo

SETUP REQUIRED (environment variables):
  BOT_TOKEN   — BotFather se milega
  OWNER_ID    — Tumhari Telegram User ID
"""

import asyncio
import logging
import time

from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode, ChatType
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import config
import pending_requests as store
from helpers import (
    build_approval_keyboard,
    build_approval_message,
    format_approved_message,
    format_rejected_message,
    format_timeout_message,
)
from executor import execute_approved_command

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
OWNER_ID = config.OWNER_ID


# ═══════════════════════════════════════════════════════════════════════════════
#   CORE INTERCEPTOR — Har group command yahan aata hai
# ═══════════════════════════════════════════════════════════════════════════════

async def intercept_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Group mein aane wali har /command ko intercept karo.
    - Owner ki khud ki commands pass through ho jaati hain (owner = boss)
    - Baaki sab ke commands owner se approve hote hain
    """
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    # Sirf group/supergroup mein kaam karo
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    # Owner khud command karega to directly allow karo — owner is the boss
    if user and user.id == OWNER_ID:
        logger.info(f"Owner command pass-through: {message.text}")
        return  # Normal handlers chalenge

    # Kya user admin hai? (non-admin commands bhi intercept karne hain agar chaho)
    # Abhi: SAARI commands intercept karein, chahe admin ho ya na ho
    # Agar sirf admin commands intercept karni hain to neeche ka block uncomment karo:
    #
    # try:
    #     member = await chat.get_member(user.id)
    #     if member.status not in ("administrator", "creator"):
    #         return  # non-admin ko ignore karo
    # except TelegramError:
    #     return

    command_text = message.text or message.caption or ""
    if not command_text.startswith("/"):
        return

    logger.info(f"Intercepted: '{command_text}' from {user.full_name} in '{chat.title}'")

    # 1️⃣ Original message delete karo (taake seedhi execution na ho)
    try:
        await message.delete()
        logger.info(f"Deleted message {message.message_id} in chat {chat.id}")
    except (BadRequest, Forbidden) as e:
        logger.warning(f"Could not delete message: {e}")
        # Delete na ho toh bhi aage badho — approval flow continue rahega

    # 2️⃣ Reply-to info collect karo (agar command kisi pe reply thi)
    reply_data = None
    if message.reply_to_message:
        rto = message.reply_to_message
        rto_user = rto.from_user
        reply_data = {
            "message_id": rto.message_id,
            "from_user_id": rto_user.id if rto_user else None,
            "from_user_name": rto_user.full_name if rto_user else "Unknown",
            "text": rto.text or rto.caption or "",
        }

    # 3️⃣ Request store mein save karo
    request_id = store.add_request(
        chat_id=chat.id,
        chat_title=chat.title or "Unknown Group",
        from_user_id=user.id,
        from_user_name=user.full_name,
        command=command_text.split()[0],   # sirf /ban wala part
        full_text=command_text,
        message_id=message.message_id,
        reply_to_message=reply_data,
    )

    # 4️⃣ Owner ko PM mein approval message bhejo
    approval_text = build_approval_message(store.get_request(request_id))
    keyboard = build_approval_keyboard(request_id)

    try:
        sent = await context.bot.send_message(
            chat_id=OWNER_ID,
            text=approval_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        store.set_bot_message_id(request_id, sent.message_id)
        logger.info(f"Approval message sent to owner for request {request_id}")

    except Forbidden:
        # Owner ne bot ko block kar rakha hai ya pehle /start nahi kiya
        logger.error("Cannot send PM to owner! Owner must /start the bot in PM first.")
        await message.reply_text(
            "⚠️ Owner ko notification nahi ja saki. "
            "Owner ko bot ka PM mein /start karna hoga.",
        )
        store.remove_request(request_id)

    except TelegramError as e:
        logger.error(f"Failed to send approval message: {e}")
        store.remove_request(request_id)

    # 5️⃣ Admin ko group mein bata do ki request gai hai owner ke paas
    try:
        notif = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                f"🔒 [{user.full_name}](tg://user?id={user.id}) ki request `{command_text.split()[0]}` "
                f"owner ke paas approval ke liye gayi hai.\n"
                f"⏳ Please wait..."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        # Ye notification 30 second baad delete karo
        context.job_queue.run_once(
            delete_notification,
            when=30,
            data={"chat_id": chat.id, "message_id": notif.message_id},
            name=f"del_notif_{notif.message_id}",
        )
    except TelegramError as e:
        logger.warning(f"Could not send group notification: {e}")


async def delete_notification(context: ContextTypes.DEFAULT_TYPE):
    """Temporary notification message delete karo."""
    job_data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=job_data["chat_id"],
            message_id=job_data["message_id"],
        )
    except TelegramError:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#   CALLBACK HANDLER — Owner ke Yes/No button press ka response
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Owner ne Yes ya No dabaya — yahan handle hoga.
    callback_data format: "approve:<request_id>" ya "reject:<request_id>"
    """
    query = update.callback_query
    user = update.effective_user

    # Sirf owner ke buttons ka response lo
    if not user or user.id != OWNER_ID:
        await query.answer("❌ Sirf owner ye kar sakta hai!", show_alert=True)
        return

    await query.answer()  # Loading spinner hatao

    data = query.data
    if ":" not in data:
        await query.edit_message_text("❌ Invalid callback data")
        return

    action, request_id = data.split(":", 1)
    request_data = store.get_request(request_id)

    if not request_data:
        await query.edit_message_text(
            "⏰ *Ye request expire ho gayi ya pehle handle ho chuki hai.*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── APPROVED ──────────────────────────────────────────────────────────────
    if action == "approve":
        logger.info(f"Owner approved request {request_id}: {request_data['full_text']}")

        # Approval message update karo (loading state)
        await query.edit_message_text(
            f"⏳ *Executing:* `{request_data['full_text']}`...",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Command actually execute karo
        success, result_msg = await execute_approved_command(context.bot, request_data)

        # Final status update
        if success:
            final_text = (
                f"✅ *Approved & Executed!*\n\n"
                f"📋 Command: `{request_data['full_text']}`\n"
                f"🏠 Group: `{request_data['chat_title']}`\n"
                f"👤 By admin: {request_data['from_user_name']}\n\n"
                f"Result: {result_msg}"
            )
        else:
            final_text = (
                f"✅ *Approved* (lekin execution mein issue)\n\n"
                f"📋 Command: `{request_data['full_text']}`\n"
                f"⚠️ {result_msg}"
            )

        await query.edit_message_text(final_text, parse_mode=ParseMode.MARKDOWN)

        # Admin ko group mein bhi bata do
        try:
            await context.bot.send_message(
                chat_id=request_data["chat_id"],
                text=(
                    f"✅ [{request_data['from_user_name']}](tg://user?id={request_data['from_user_id']}) "
                    f"ki `{request_data['command']}` request owner ne approve kar di!\n"
                    f"{result_msg}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramError as e:
            logger.warning(f"Could not notify group about approval: {e}")

    # ── REJECTED ──────────────────────────────────────────────────────────────
    elif action == "reject":
        logger.info(f"Owner rejected request {request_id}: {request_data['full_text']}")

        await query.edit_message_text(
            f"❌ *Rejected!*\n\n"
            f"📋 Command: `{request_data['full_text']}`\n"
            f"🏠 Group: `{request_data['chat_title']}`\n"
            f"👤 Admin: {request_data['from_user_name']}",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Admin ko group mein rejection bata do
        try:
            await context.bot.send_message(
                chat_id=request_data["chat_id"],
                text=(
                    f"❌ [{request_data['from_user_name']}](tg://user?id={request_data['from_user_id']}) "
                    f"ki `{request_data['command']}` request *owner ne reject kar di*."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramError as e:
            logger.warning(f"Could not notify group about rejection: {e}")

    # Store se hatao
    store.remove_request(request_id)


# ═══════════════════════════════════════════════════════════════════════════════
#   /start COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        if user.id == OWNER_ID:
            text = (
                "👑 *Welcome Boss!*\n\n"
                "Main GateKeeper Bot hoon. Jab bhi koi admin group mein "
                "koi `/command` bhejega, toh main pehle tumse approve karunga.\n\n"
                "✅ Ye message aa jana matlab main PM mein messages bhej sakta hoon.\n\n"
                "📌 *Kaise kaam karta hai:*\n"
                "1. Bot ko group mein add karo (admin banana zaroori hai)\n"
                "2. Koi bhi admin command bhejega\n"
                "3. Tum yahan Yes/No kar sakte ho\n\n"
                "📋 /status — pending requests dekho\n"
                "📋 /help — help dekho"
            )
        else:
            text = (
                "🤖 *GateKeeper Bot*\n\n"
                "Main ek restriction bot hoon. Is group ka owner "
                "sab commands approve karta hai.\n\n"
                f"Owner: @{config.OWNER_USERNAME}"
            )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        # Group mein /start — intercept_command handle karega
        pass


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type != ChatType.PRIVATE:
        return  # Group mein help mat bhejo

    if user.id == OWNER_ID:
        text = (
            "📖 *GateKeeper Bot — Owner Commands*\n\n"
            "/start — Bot start/check karo\n"
            "/help — Ye message\n"
            "/status — Pending requests ki list\n"
            "/clearall — Saari pending requests clear karo\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Intercepted Commands (group mein):*\n"
            "Saari `/commands` intercept hoti hain — /ban, /unban,\n"
            "/mute, /unmute, /kick, /purge, /pin, /promote,\n"
            "/demote, /warn, aur koi bhi custom command\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ *Config:*\n"
            f"Owner ID: `{OWNER_ID}`\n"
            f"Request Timeout: `{config.REQUEST_TIMEOUT}s`"
        )
    else:
        text = (
            "🤖 *GateKeeper Bot*\n"
            "Main group admin commands ko owner se approve karata hoon."
        )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pending requests ki list — sirf owner ke liye."""
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return

    reqs = store.pending_requests
    if not reqs:
        await update.message.reply_text("✅ Koi pending request nahi hai!")
        return

    lines = [f"📋 *{len(reqs)} Pending Request(s):*\n"]
    for rid, data in list(reqs.items())[:10]:  # Max 10 dikhao
        age = int(time.time() - data["timestamp"])
        lines.append(
            f"• `{data['command']}` by {data['from_user_name']}\n"
            f"  Group: {data['chat_title']} | {age}s ago\n"
            f"  ID: `{rid}`"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_clearall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saari pending requests clear karo — sirf owner."""
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return

    count = len(store.pending_requests)
    store.pending_requests.clear()
    await update.message.reply_text(f"🗑️ `{count}` pending requests clear kar diye.", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#   PERIODIC CLEANUP JOB
# ═══════════════════════════════════════════════════════════════════════════════

async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    """Expired requests clean karo aur owner ko inform karo."""
    expired_count = store.cleanup_expired(config.REQUEST_TIMEOUT)
    if expired_count > 0:
        logger.info(f"Cleaned up {expired_count} expired requests")
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"⏰ `{expired_count}` pending request(s) timeout ke baad expire ho gayi.",
                parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#   APPLICATION SETUP & MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    logger.info("Starting GateKeeper Bot...")
    logger.info(f"Owner ID: {OWNER_ID}")

    # Application build karo
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    # ── Handlers Register karo ──────────────────────────────────────────────

    # 1. /start aur /help — Private chat mein (owner ke liye)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("clearall", cmd_clearall, filters=filters.ChatType.PRIVATE))

    # 2. Inline button callbacks (Yes/No)
    app.add_handler(CallbackQueryHandler(handle_approval_callback))

    # 3. ⭐ MAIN INTERCEPTOR — Group/Supergroup mein aane wali SAARI /commands
    #    Priority 1 (high) taaki pehle chale
    app.add_handler(
        MessageHandler(
            filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            intercept_command,
        ),
        group=1,  # Handler group 1 — pehle chale
    )

    # ── Periodic Cleanup Job ─────────────────────────────────────────────────
    job_queue = app.job_queue
    job_queue.run_repeating(
        cleanup_job,
        interval=60,   # Har 60 second mein check karo
        first=60,
        name="cleanup_expired_requests",
    )

    # ── Start Polling ────────────────────────────────────────────────────────
    logger.info("Bot is running! Polling for updates...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,  # Restart pe purane updates ignore karo
    )


if __name__ == "__main__":
    main()
