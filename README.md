# GateKeeper Bot v2 🔒

Telegram group mein koi bhi admin command direct execute nahi hogi.
Pehle owner se YES/NO approval lena padega.

---

## Problem Fix (v2)

**Original issue:** Owner "No" press karne ke baad bhi command execute ho rahi thi.

**Root cause:** `execute_approved_command()` galat jagah call ho raha tha.

**Fix:** Ab executor **sirf** `approve` action pe chalta hai. `reject` pe bilkul nahi.

---

## Kaise kaam karta hai

```
Admin → /ban @user
   ↓
Bot turant message DELETE karta hai
   ↓
Owner ko PM: "Hey Boss! Yes/No?"
   ↓
Owner YES → Bot /ban execute karta hai
Owner NO  → KUCH NAHI HOTA (command block)
```

### MissRose block kaise hoti hai?

Telegram mein ek bot doosre bot ko directly nahi rok sakta.
Lekin hamara bot admin ka **message delete** kar deta hai **pehle**.
Jab message Telegram server pe exist hi nahi karta,
MissRose ko command milti hi nahi.

**Isliye ye zaroori hai:**
- Hamara bot ko **Delete Messages** admin permission chahiye
- Hamara bot admin list mein **MissRose se PEHLE** hona chahiye

---

## Setup Guide

### Step 1 — Bot banao
1. [@BotFather](https://t.me/BotFather) pe `/newbot`
2. Token save karo

### Step 2 — Apni User ID lo
[@userinfobot](https://t.me/userinfobot) pe `/start` bhejo → ID note karo

### Step 3 — Bot ko group mein add karo
1. Group → Settings → Add Members → apna bot add karo
2. Bot ko **Admin** banao with ye permissions:
   - ✅ Delete Messages **(MUST HAVE)**
   - ✅ Ban Users
   - ✅ Restrict Members
   - ✅ Pin Messages
   - ✅ Invite Users via Link

### Step 4 — Admin order set karo (CRITICAL!)
Group → Administrators list mein:
- Hamara GatekeeperBot **UPAR** hona chahiye
- @MissRose_bot **NEECHE** hona chahiye

Telegram admins ko sequentially process karta hai — pehle wala bot message dekhega pehle.

### Step 5 — Owner PM setup
Bot ka username open karo → `/start` bhejo
(Ye zaroori hai taaki bot tumhe PM bhej sake)

---

## Render.com Deployment

### Environment Variables (Render Dashboard mein set karo):

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | BotFather se mila token |
| `OWNER_ID` | Tumhari Telegram User ID |
| `OWNER_USERNAME` | Tumhara username (@ ke bina) |
| `REQUEST_TIMEOUT` | `300` (5 minutes, optional) |

### Build & Start Commands:

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python -u bot.py
```

### Docker deploy (recommended):
Render pe "Docker" select karo — Dockerfile automatically use hoga.

---

## Supported Commands (Intercept hoti hain)

| Command | Kya karta hai |
|---------|--------------|
| `/ban` | User ban |
| `/unban` | User unban |
| `/mute` | User mute (time support: 1h, 30m, 2d) |
| `/unmute` | User unmute |
| `/kick` | User kick |
| `/purge` | Messages purge |
| `/pin` | Message pin |
| `/unpin` | Message unpin |
| `/unpinall` | Saare unpin |
| `/promote` | Admin promote |
| `/demote` | Admin demote |
| `/warn` | Warning |
| `/del` | Single message delete |
| Koi bhi `/command` | Intercept + owner notification |

---

## Owner Commands (PM mein)

- `/start` — Bot check + PM confirm
- `/help` — Full guide
- `/status` — Pending requests list
- `/clearall` — Saari pending requests clear

---

## Troubleshooting

**"No" ke baad bhi command execute hoti hai?**
→ Check karo ki bot ko "Delete Messages" permission hai
→ Bot admin list mein MissRose se PEHLE hai?

**Bot PM nahi bhej raha?**
→ Bot ke PM mein `/start` bhejo pehle

**Delete fail ho raha hai?**
→ Bot ko group mein "Delete Messages" admin permission do
