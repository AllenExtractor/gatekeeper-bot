"""
bot.py — GateKeeper Bot v2 (Advanced)
======================================

CRITICAL FIX:
- No press karne ke baad bhi command execute ho rahi thi — AB FIX HAI
- Har command TURANT delete hoti hai (0ms delay)
- Owner YES kare tabhi executor chalega — NO pe bilkul nahi
- MissRose / any other bot tak command PAHUNCHE HI NAHI kyunki message
  delete ho chuka hota hai Telegram server se

FLOW:
1. Group mein koi ADMIN koi bhi /command bhejta hai
2. Bot TURANT message delete karta hai (before any other bot processes it)
3. Bot Owner ko PM mein "Hey Boss! Yes/No" bhejta hai
4. Owner YES → bot khud execute karta hai (executor.py)
5. Owner NO  → KUCH NAHI HOTA — silently reject, admin ko batao

IMPORTANT — MissRose block kaise hota hai:
  Telegram mein ek bot doosre bot ki command nahi rok sakta directly.
  Lekin agar hamara bot message DELETE kar de PEHLE, toh MissRose ko
  command milti hi nahi (message exist nahi karta).
  Isliye bot ko "Delete Messages" permission zaroori hai aur
  list mein PEHLE hona chahiye (setup guide mein explain hai).

SETUP (environment variables):
  BOT_TOKEN     — BotFather se milega
  OWNER_ID      — Tumhari Telegram User ID (hardcoded fallback bhi hai)
  OWNER_USERNAME — Optional, display ke liye
"""

import asyncio
import logging
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMemberAdministrator,
    ChatMemberOwner,
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
)
from executor import execute_approved_command

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

OWNER_ID = config.OWNER_ID


# ═══════════════════════════════════════════════════════════════════════════════
#   HELPER — Is user admin hai?
# ═══════════════════════════════════════════════════════════════════════════════

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check karo ki user admin ya owner hai group mein."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
    except TelegramError:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#   CORE INTERCEPTOR — Har group command yahan aata hai
# ═══════════════════════════════════════════════════════════════════════════════

async def intercept_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Group mein aane wali har /command ko intercept karo.

    KEY BEHAVIOR:
    - Owner ki commands: directly pass through (owner is boss)
    - Normal users ki commands: silently ignore (non-admins can't do admin stuff anyway)
    - Admin ki commands: TURANT DELETE karo, phir owner se approval lo

    WHY DELETE FIRST:
    Message delete hone ke baad koi bhi bot (MissRose etc.) us command ko
    process nahi kar sakta — message Telegram server se gone ho jaata hai.
    """
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    # Sirf group/supergroup mein kaam karo
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    # User exist karna chahiye
    if not user:
        return

    # Owner khud command kare to directly allow karo
    if user.id == OWNER_ID:
        logger.info(f"Owner command pass-through: {message.text}")
        return

    # Command text check
    command_text = message.text or message.caption or ""
    if not command_text.startswith("/"):
        return

    # ── ADMIN CHECK ──────────────────────────────────────────────────────────
    # Sirf admin ki commands intercept karo
    # Non-admin ki commands already Telegram level pe restricted hain mostly
    # Lekin extra safety ke liye hum sirf admin commands process karte hain
    admin_check = await is_admin(context.bot, chat.id, user.id)
    if not admin_check:
        # Non-admin ne command try ki — silently delete karo aur ignore
        try:
            await message.delete()
        except (BadRequest, Forbidden):
            pass
        logger.info(f"Non-admin {user.full_name} tried command {command_text} — deleted & ignored")
        return

    logger.info(f"Intercepted admin command: '{command_text}' from {user.full_name} in '{chat.title}'")

    # ── STEP 1: TURANT MESSAGE DELETE ────────────────────────────────────────
    # Ye sabse zaroori step hai — pehle delete, phir kuch bhi
    # Agar delete ho gaya to MissRose ya koi bhi bot is command ko nahi dekhega
    deleted_successfully = False
    try:
        await message.delete()
        deleted_successfully = True
        logger.info(f"✅ Message {message.message_id} DELETED immediately")
    except (BadRequest, Forbidden) as e:
        logger.warning(f"⚠️ Could not delete message: {e}")
        # Delete fail — bot ko "Delete Messages" permission nahi hai
        # Approval flow phir bhi chalega lekin MissRose block nahi hogi

    # ── STEP 2: Reply-to info collect karo ──────────────────────────────────
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

    # ── STEP 3: Request store mein save karo ────────────────────────────────
    request_id = store.add_request(
        chat_id=chat.id,
        chat_title=chat.title or "Unknown Group",
        from_user_id=user.id,
        from_user_name=user.full_name,
        command=command_text.split()[0],
        full_text=command_text,
        message_id=message.message_id,
        reply_to_message=reply_data,
        delete_success=deleted_successfully,
    )

    # ── STEP 4: Owner ko PM mein approval bhejo ──────────────────────────────
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
        logger.error("Cannot PM owner! Owner must /start the bot in PM first.")
        store.remove_request(request_id)
        return

    except TelegramError as e:
        logger.error(f"Failed to send approval message: {e}")
        store.remove_request(request_id)
        return

    # ── STEP 5: Admin ko group mein temporary notification ──────────────────
    try:
        notif = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                f"🔒 [{user.full_name}](tg://user?id={user.id}) ki request "
                f"`{command_text.split()[0]}` "
                f"owner ke paas approval ke liye gayi hai.\n"
                f"⏳ Please wait..."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        # 30 second baad delete karo
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
#   CALLBACK HANDLER — Owner ke Yes/No button press
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Owner ne Yes ya No dabaya.

    CRITICAL FIX:
    - YES  → execute_approved_command() call karo
    - NO   → BILKUL KUCH MAT KARO sirf reject message update karo
             Executor KABHI NAHI chalega NO pe
    """
    query = update.callback_query
    user = update.effective_user

    # Sirf owner ke buttons
    if not user or user.id != OWNER_ID:
        await query.answer("❌ Sirf owner ye kar sakta hai!", show_alert=True)
        return

    await query.answer()

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
        logger.info(f"Owner APPROVED request {request_id}: {request_data['full_text']}")

        await query.edit_message_text(
            f"⏳ *Executing:* `{request_data['full_text']}`...",
            parse_mode=ParseMode.MARKDOWN,
        )

        # ✅ YES pe hi executor chalega
        success, result_msg = await execute_approved_command(context.bot, request_data)

        if success:
            final_text = (
                f"✅ *Approved & Executed!*\n\n"
                f"📋 Command: `{request_data['full_text']}`\n"
                f"🏠 Group: `{request_data['chat_title']}`\n"
                f"👤 Admin: {request_data['from_user_name']}\n\n"
                f"Result: {result_msg}"
            )
        else:
            final_text = (
                f"✅ *Approved* (lekin execution mein issue)\n\n"
                f"📋 Command: `{request_data['full_text']}`\n"
                f"⚠️ {result_msg}"
            )

        await query.edit_message_text(final_text, parse_mode=ParseMode.MARKDOWN)

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
        logger.info(f"Owner REJECTED request {request_id}: {request_data['full_text']}")

        # ❌ NO pe SIRF message update — executor NAHI chalega
        await query.edit_message_text(
            f"❌ *Rejected!*\n\n"
            f"📋 Command: `{request_data['full_text']}`\n"
            f"🏠 Group: `{request_data['chat_title']}`\n"
            f"👤 Admin: {request_data['from_user_name']}\n\n"
            f"_Command block kar di gayi — koi action nahi hua._",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Admin ko group mein batao ki reject hua
        try:
            reject_notif = await context.bot.send_message(
                chat_id=request_data["chat_id"],
                text=(
                    f"❌ [{request_data['from_user_name']}](tg://user?id={request_data['from_user_id']}) "
                    f"ki `{request_data['command']}` request *owner ne reject kar di*."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            # Rejection notification bhi 30s mein delete
            context.job_queue.run_once(
                delete_notification,
                when=30,
                data={"chat_id": request_data["chat_id"], "message_id": reject_notif.message_id},
                name=f"del_notif_{reject_notif.message_id}",
            )
        except TelegramError as e:
            logger.warning(f"Could not notify group about rejection: {e}")

    # Request store se remove karo
    store.remove_request(request_id)


# ═══════════════════════════════════════════════════════════════════════════════
#   OWNER COMMANDS (Private Chat)
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == ChatType.PRIVATE:
        if user.id == OWNER_ID:
            text = (
                "👑 *Welcome Boss!*\n\n"
                "Main GateKeeper Bot v2 hoon.\n\n"
                "✅ PM connection confirmed — notifications aayenge.\n\n"
                "📌 *Kaise kaam karta hai:*\n"
                "1. Bot ko group mein add karo\n"
                "2. Bot ko *Admin* banao with *Delete Messages* permission\n"
                "3. Bot ko list mein *MissRose se PEHLE* rakho (important!)\n"
                "4. Koi admin command bhejega → tum approve/reject karo\n\n"
                "📋 /status — pending requests\n"
                "📋 /help — full guide"
            )
        else:
            text = (
                "🤖 *GateKeeper Bot*\n\n"
                "Main ek restriction bot hoon.\n"
                f"Owner: @{config.OWNER_USERNAME}"
            )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type != ChatType.PRIVATE:
        return

    if user.id == OWNER_ID:
        text = (
            "📖 *GateKeeper Bot v2 — Help*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Owner Commands (PM mein):*\n"
            "/start — Bot check\n"
            "/help — Ye message\n"
            "/status — Pending requests\n"
            "/clearall — Saari requests clear\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Group Setup (ZAROORI):*\n"
            "1️⃣ Bot ko group mein add karo\n"
            "2️⃣ Bot ko Admin banao:\n"
            "   ✅ Delete Messages — MUST HAVE\n"
            "   ✅ Ban Users\n"
            "   ✅ Restrict Members\n"
            "   ✅ Pin Messages\n"
            "3️⃣ Admin list mein is bot ko\n"
            "   MissRose se UPAR rakho\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Intercepted Commands:*\n"
            "/ban /unban /mute /unmute\n"
            "/kick /purge /pin /unpin\n"
            "/promote /demote /warn\n"
            "aur koi bhi / wali command\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ Owner ID: `{OWNER_ID}`\n"
            f"⏱ Timeout: `{config.REQUEST_TIMEOUT}s`"
        )
    else:
        text = (
            "🤖 *GateKeeper Bot*\n"
            "Group admin commands owner se approve hoti hain."
        )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return

    reqs = store.pending_requests
    if not reqs:
        await update.message.reply_text("✅ Koi pending request nahi hai!")
        return

    lines = [f"📋 *{len(reqs)} Pending Request(s):*\n"]
    for rid, data in list(reqs.items())[:10]:
        age = int(time.time() - data["timestamp"])
        lines.append(
            f"• `{data['command']}` by {data['from_user_name']}\n"
            f"  Group: {data['chat_title']} | {age}s ago\n"
            f"  ID: `{rid}`"
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_clearall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return

    count = len(store.pending_requests)
    store.pending_requests.clear()
    await update.message.reply_text(
        f"🗑️ `{count}` pending requests clear kar diye.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#   PERIODIC CLEANUP JOB
# ═══════════════════════════════════════════════════════════════════════════════

async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    """Expired requests clean karo."""
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
#   HEALTH CHECK SERVER
# ═══════════════════════════════════════════════════════════════════════════════

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"GateKeeper Bot v2 is alive!")

    def log_message(self, format, *args):
        pass


def start_health_server(port: int = 8000):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()


# ═══════════════════════════════════════════════════════════════════════════════
#   MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    logger.info("Starting GateKeeper Bot v2...")
    logger.info(f"Owner ID: {OWNER_ID}")

    port = int(os.environ.get("PORT", 8000))
    health_thread = threading.Thread(target=start_health_server, args=(port,), daemon=True)
    health_thread.start()

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    # ── Private chat handlers ─────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("clearall", cmd_clearall, filters=filters.ChatType.PRIVATE))

    # ── Inline button callbacks ───────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_approval_callback))

    # ── MAIN INTERCEPTOR — Group commands ─────────────────────────────────────
    # group=0 (highest priority) — pehle chale, kisi bhi handler se pehle
    app.add_handler(
        MessageHandler(
            filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            intercept_command,
        ),
        group=0,
    )

    # ── Cleanup job ───────────────────────────────────────────────────────────
    app.job_queue.run_repeating(
        cleanup_job,
        interval=60,
        first=60,
        name="cleanup_expired_requests",
    )

    logger.info("Bot is running! Polling for updates...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
