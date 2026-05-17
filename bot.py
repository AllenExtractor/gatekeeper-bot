"""
bot.py — GateKeeper Bot (Bot API side)
=======================================

Ye bot sirf ye kaam karta hai:
1. Owner ke PM mein Yes/No handle karna (callback)
2. Owner ke /start /help /status commands handle karna
3. Userbot se aaye requests execute karna (approve pe)

Command interception ab USERBOT karta hai (userbot.py)
Userbot MTProto level pe message delete karta hai — Rose se PEHLE.
"""

import asyncio
import logging
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
from executor import execute_approved_command

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

OWNER_ID = config.OWNER_ID


# ═══════════════════════════════════════════════════════════════════════════════
#   CALLBACK HANDLER — Owner ke Yes/No
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Owner ne Yes ya No dabaya.

    YES  → execute_approved_command() — task hoga
    NO   → KUCH NAHI — sirf reject message, executor kabhi nahi chalta
    """
    query = update.callback_query
    user = update.effective_user

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
        logger.info(f"Owner APPROVED: {request_data['full_text']}")

        await query.edit_message_text(
            f"⏳ *Executing:* `{request_data['full_text']}`...",
            parse_mode=ParseMode.MARKDOWN,
        )

        # ✅ Sirf YES pe execute hoga
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
                f"✅ *Approved* (execution mein issue)\n\n"
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
            logger.warning(f"Group notify failed: {e}")

    # ── REJECTED ──────────────────────────────────────────────────────────────
    elif action == "reject":
        logger.info(f"Owner REJECTED: {request_data['full_text']}")

        # ❌ NO pe executor NAHI chalta — bilkul kuch nahi hota
        await query.edit_message_text(
            f"❌ *Rejected!*\n\n"
            f"📋 Command: `{request_data['full_text']}`\n"
            f"🏠 Group: `{request_data['chat_title']}`\n"
            f"👤 Admin: {request_data['from_user_name']}\n\n"
            f"_Command block kar di gayi — koi action nahi hua._",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            rej_msg = await context.bot.send_message(
                chat_id=request_data["chat_id"],
                text=(
                    f"❌ [{request_data['from_user_name']}](tg://user?id={request_data['from_user_id']}) "
                    f"ki `{request_data['command']}` request *owner ne reject kar di*."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            # 30s mein delete
            context.job_queue.run_once(
                _delete_msg,
                when=30,
                data={"chat_id": request_data["chat_id"], "message_id": rej_msg.message_id},
            )
        except TelegramError as e:
            logger.warning(f"Reject notify failed: {e}")

    store.remove_request(request_id)


async def _delete_msg(context: ContextTypes.DEFAULT_TYPE):
    d = context.job.data
    try:
        await context.bot.delete_message(chat_id=d["chat_id"], message_id=d["message_id"])
    except TelegramError:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#   OWNER COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat.type != ChatType.PRIVATE:
        return
    if user.id == OWNER_ID:
        text = (
            "👑 *Welcome Boss!*\n\n"
            "GateKeeper Bot + Userbot dono active hain.\n\n"
            "✅ PM confirmed — notifications ready.\n\n"
            "📌 *System:*\n"
            "• Userbot → MTProto se command intercept\n"
            "• Bot API → Owner approval handle\n"
            "• Ye combo MissRose se bhi PEHLE kaam karta hai\n\n"
            "/status — pending requests\n"
            "/help — full guide"
        )
    else:
        text = f"🤖 *GateKeeper Bot*\nOwner: @{config.OWNER_USERNAME}"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat.type != ChatType.PRIVATE:
        return
    if user.id != OWNER_ID:
        await update.message.reply_text("🤖 GateKeeper Bot — Admin commands owner se approve hoti hain.")
        return

    text = (
        "📖 *GateKeeper Bot — Help*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "*Owner Commands:*\n"
        "/start — Check\n"
        "/help — Ye message\n"
        "/status — Pending requests\n"
        "/clearall — Saari requests clear\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "*Intercepted Commands:*\n"
        "/ban /unban /mute /unmute /kick\n"
        "/purge /pin /unpin /promote /demote\n"
        "/warn /del aur baaki saari / commands\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Owner ID: `{OWNER_ID}`\n"
        f"⏱ Timeout: `{config.REQUEST_TIMEOUT}s`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return
    reqs = store.pending_requests
    if not reqs:
        await update.message.reply_text("✅ Koi pending request nahi!")
        return
    lines = [f"📋 *{len(reqs)} Pending:*\n"]
    for rid, d in list(reqs.items())[:10]:
        age = int(time.time() - d["timestamp"])
        lines.append(
            f"• `{d['command']}` by {d['from_user_name']}\n"
            f"  {d['chat_title']} | {age}s ago"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_clearall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return
    count = len(store.pending_requests)
    store.pending_requests.clear()
    await update.message.reply_text(f"🗑️ `{count}` requests clear.", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#   CLEANUP JOB
# ═══════════════════════════════════════════════════════════════════════════════

async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    expired = store.cleanup_expired(config.REQUEST_TIMEOUT)
    if expired > 0:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"⏰ `{expired}` request(s) timeout expire ho gayi.",
                parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#   HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"GateKeeper Bot + Userbot is alive!")
    def log_message(self, *args):
        pass


def start_health_server(port=8000):
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()


# ═══════════════════════════════════════════════════════════════════════════════
#   BUILD APP (main.py ke liye)
# ═══════════════════════════════════════════════════════════════════════════════

def build_app() -> Application:
    """Application object banao aur return karo."""
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("clearall", cmd_clearall, filters=filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(handle_approval_callback))

    app.job_queue.run_repeating(cleanup_job, interval=60, first=60)

    return app
