import os

# ============================================================
#   GATEKEEPER BOT v2 — CONFIG
# ============================================================

# Bot Token (BotFather se milega)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Owner Telegram User ID (hardcoded fallback)
# Apni ID jaanne ke liye @userinfobot pe /start bhejo
OWNER_ID = int(os.environ.get("OWNER_ID", "8446475678"))

# Owner username (@ ke bina) - sirf display ke liye
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "SmartBoy_ApnaMS")

# Pending requests timeout (seconds) — itne baad auto-expire
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))  # 5 minutes
