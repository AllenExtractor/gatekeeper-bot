"""
generate_session.py
====================
String Session generate karne ke liye ye script chalao.

KAISE CHALAO:
  1. Apne PC pe Python install hona chahiye
  2. Terminal/CMD mein:
       pip install pyrogram TgCrypto
       python generate_session.py
  3. Apna phone number enter karo (+92xxxxxxxxxx format mein)
  4. Telegram pe aaya OTP enter karo
  5. Agar 2FA hai toh password bhi enter karo
  6. Screen pe aayega: "YOUR STRING SESSION: BQA...=="
  7. Woh poori string copy karo aur config.py mein STRING_SESSION mein paste karo

NOTE: Ye script sirf ek baar chalani hai.
      Render pe ye file upload mat karna — sirf config.py mein value paste karo.
"""

from pyrogram import Client

# ── Yahan apni values daalo ──────────────────────────────────
API_ID = 00000000          # my.telegram.org se
API_HASH = "PASTE_HERE"    # my.telegram.org se
# ─────────────────────────────────────────────────────────────

print("=" * 50)
print("  GateKeeper — String Session Generator")
print("=" * 50)
print()

with Client(
    name="session_generator",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True,
) as app:
    session = app.export_session_string()
    print()
    print("=" * 50)
    print("  YOUR STRING SESSION (copy karo):")
    print("=" * 50)
    print()
    print(session)
    print()
    print("=" * 50)
    print("  Ye string config.py mein STRING_SESSION mein paste karo")
    print("=" * 50)
