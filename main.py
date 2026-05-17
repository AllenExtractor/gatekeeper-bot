"""
main.py — Entry Point
======================

Ye DONO chalaata hai ek saath:
1. Pyrogram Userbot  → MTProto, command intercept (Rose se PEHLE)
2. python-telegram-bot → Bot API, owner approval handle

Dono ek hi asyncio event loop mein run karte hain.
"""

import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import config
import userbot as ub
from bot import build_app

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Health Check Server ─────────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"GateKeeper alive!")
    def log_message(self, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 8000))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    logger.info("=" * 50)
    logger.info("  GateKeeper Bot — Starting...")
    logger.info(f"  Owner ID : {config.OWNER_ID}")
    logger.info("=" * 50)

    # Health server — background thread
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    # ── Bot API Application build karo ───────────────────────────────────────
    app = build_app()

    # ── Userbot ko bot app ka reference do ───────────────────────────────────
    # Taaki userbot owner ko notification bhej sake bot ke through
    ub.set_bot_app(app)

    # ── Initialize bot app ────────────────────────────────────────────────────
    await app.initialize()
    await app.start()

    # ── Userbot start karo ────────────────────────────────────────────────────
    await ub.start_userbot()

    logger.info("✅ Both Bot API and Userbot are running!")
    logger.info("✅ Commands will be intercepted BEFORE MissRose")

    # ── Polling start karo (bot API) ──────────────────────────────────────────
    await app.updater.start_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )

    logger.info("✅ All systems running. Press Ctrl+C to stop.")

    # ── Jab tak chale ─────────────────────────────────────────────────────────
    try:
        await asyncio.Event().wait()  # Infinite wait
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await ub.stop_userbot()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
