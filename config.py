import os

# ============================================================
#   GATEKEEPER BOT — CONFIG
#   Sirf ye variables set karo aur bot ready hai
# ============================================================

# Apna Bot Token (BotFather se milega)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Tumhari Telegram User ID (hardcoded owner)
# Apni ID janane ke liye @userinfobot pe /start bhejo
OWNER_ID = int(os.environ.get("OWNER_ID", "8446475678"))

# Owner ka username (@ ke bina) - optional, sirf display ke liye
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "@SmartBoy_ApnaMS")

# Pending requests ka timeout (seconds) — itne time baad auto-expire
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))  # 5 minutes default
