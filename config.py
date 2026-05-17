# ============================================================
#   GATEKEEPER BOT — CONFIG
#   Neeche saari values paste karo — bas itna kaam hai
# ============================================================

# ── Telegram Bot (BotFather se) ──────────────────────────────
BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
# Example: "7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ── Owner Info ───────────────────────────────────────────────
OWNER_ID = 0000000000
# Example: 8446475678
# Apni ID jaanno: @userinfobot pe /start bhejo

OWNER_USERNAME = "PASTE_YOUR_USERNAME_HERE"
# Example: "SmartBoy_ApnaMS"  (@ ke bina)

# ── Userbot Credentials (my.telegram.org se) ─────────────────
API_ID = 00000000
# Example: 12345678

API_HASH = "PASTE_YOUR_API_HASH_HERE"
# Example: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"

STRING_SESSION = "PASTE_YOUR_STRING_SESSION_HERE"
# Kaise banao:
#   1. apne PC pe run karo:
#      pip install pyrogram TgCrypto
#   2. Ye script chalao (generate_session.py):
#      from pyrogram import Client
#      with Client("tmp", api_id=API_ID, api_hash=API_HASH) as app:
#          print(app.export_session_string())
#   3. Phone pe OTP aayega → paste karo → session string print hogi
#   4. Woh yahan paste karo
# Example: "BQA...long_string...=="

# ── Settings ─────────────────────────────────────────────────
REQUEST_TIMEOUT = 300   # Seconds — kitne time mein request expire ho (default 5 min)
