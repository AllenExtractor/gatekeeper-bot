# GateKeeper Bot + Userbot 🔒

MissRose se PEHLE command intercept karta hai — MTProto level pe.

---

## Kaise Kaam Karta Hai

```
Admin → /mute bheja
    ↓
Userbot (MTProto) — Telegram server level pe SEEDHA receive karta hai
    ↓
Userbot TURANT message DELETE karta hai
(MissRose ko message milne se PEHLE — isliye Rose execute nahi kar sakti)
    ↓
Bot API → Owner ko PM: "Hey Boss! Yes / No?"
    ↓
Owner YES → Bot execute karta hai
Owner NO  → KUCH NAHI HOTA (100% block)
```

---

## Step 1 — config.py Fill Karo

`config.py` kholo aur ye values paste karo:

### BOT_TOKEN
BotFather pe `/newbot` → Token milega
```
BOT_TOKEN = "7123456789:AAFxxxxxxxxxxxxxxx"
```

### OWNER_ID
[@userinfobot](https://t.me/userinfobot) pe `/start` bhejo → ID milegi
```
OWNER_ID = 8446475678
```

### API_ID aur API_HASH
1. [my.telegram.org](https://my.telegram.org) pe jao
2. Login karo (phone number se)
3. "API development tools" pe click karo
4. App banao → `api_id` aur `api_hash` milega
```
API_ID = 12345678
API_HASH = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
```

### STRING_SESSION — Kaise Banao

**Apne PC pe ye karo (ek baar):**

```bash
pip install pyrogram TgCrypto
```

`generate_session.py` kholo → API_ID aur API_HASH daalo → Run karo:
```bash
python generate_session.py
```

- Phone number maangega → daalo
- OTP aayega Telegram pe → daalo
- Agar 2FA hai → password daalo
- Screen pe string aayegi → copy karo → config.py mein paste karo

```
STRING_SESSION = "BQA...bahut_lamba_string...=="
```

---

## Step 2 — Render.com Deploy

1. GitHub pe naya repo banao → saari files upload karo
2. Render.com pe "New Web Service" → repo connect karo
3. **Docker** select karo (Dockerfile auto use hoga)
4. Deploy karo

**Build Command:** (Docker use karne pe automatically hoga)
```
pip install -r requirements.txt
```

**Start Command:**
```
python -u main.py
```

---

## Step 3 — Group Setup

1. Bot ko group mein add karo
2. **Bot ko Admin banao** — ye permissions do:
   - ✅ Delete Messages **(ZAROORI)**
   - ✅ Ban Users
   - ✅ Restrict Members
   - ✅ Pin Messages
3. Bot ko `/start` karo PM mein (owner account se)
4. **Userbot account** ko bhi group mein add karo (admin banana zaroori nahi — member hi kaafi hai)

---

## Files Structure

```
gatekeeper-userbot/
├── main.py              ← Entry point (ye chalao)
├── bot.py               ← Bot API — owner approval
├── userbot.py           ← Pyrogram userbot — command intercept
├── executor.py          ← Commands execute karta hai (approve pe)
├── config.py            ← ⭐ YAHAN SAARI VALUES PASTE KARO
├── pending_requests.py  ← In-memory request store
├── helpers.py           ← Utility functions
├── generate_session.py  ← String session banane ka tool
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Troubleshooting

**Userbot start nahi ho raha?**
→ STRING_SESSION check karo — sahi hai?
→ API_ID aur API_HASH sahi hain?

**Delete nahi ho raha?**
→ Userbot account group mein add hai?
→ Bot ko "Delete Messages" permission hai?

**Owner ko message nahi aa raha?**
→ Bot ke PM mein `/start` bhejo pehle
