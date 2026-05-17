# 🔒 GateKeeper Bot

**Ek Telegram Bot jo group mein kisi bhi admin command ko owner ki permission ke baghair execute nahi hone deta.**

---

## ✨ Features

- 🚫 Group mein har `/command` intercept hoti hai
- 👑 Owner ko PM mein **Yes / No** buttons ke saath approval request aati hai
- ✅ Yes → command execute ho jaati hai group mein
- ❌ No → command block ho jaati hai, admin ko notify kiya jaata hai
- ⏰ Timeout support (5 min default, configurable)
- 📋 `/status` se pending requests dekho
- 🔒 Owner ki apni commands directly execute hoti hain (boss hai!)

---

## 📁 Project Structure

```
gatekeeper-bot/
├── bot.py              # Main bot file — handlers, flow
├── config.py           # Configuration (env variables)
├── pending_requests.py # In-memory request store
├── executor.py         # Command execution logic
├── helpers.py          # Utility functions (messages, keyboards)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker deployment
├── .env.example        # Environment variables template
├── .gitignore
└── README.md
```

---

## ⚙️ Setup

### Step 1: Bot Token Lo

1. Telegram pe [@BotFather](https://t.me/BotFather) pe jao
2. `/newbot` send karo
3. Naam aur username do
4. Token copy karo (aise dikhega: `1234567890:ABCdef...`)

### Step 2: Owner ID Lo

[@userinfobot](https://t.me/userinfobot) pe `/start` bhejo — tumhari User ID mil jaayegi.

### Step 3: Bot ko Group mein Add karo

1. Bot ko group mein add karo
2. **Admin banana zaroori hai** (Delete Messages permission chahiye)
3. Bot permissions: ✅ Delete Messages, ✅ Ban Users, ✅ Restrict Members, ✅ Pin Messages

### Step 4: Owner PM Setup

Pehle baar **tumhe bot ka PM mein `/start` karna hoga** — warna bot tumhe messages nahi bhej sakta.

---

## 🚀 Render.com pe Deploy karna

### Method: Docker (Recommended)

#### Step 1: GitHub pe Push karo

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TUMHARA_USERNAME/gatekeeper-bot.git
git push -u origin main
```

#### Step 2: Render.com pe Service Banao

1. [render.com](https://render.com) pe jao → **New +** → **Web Service**
2. GitHub repo connect karo
3. Settings:
   - **Name:** `gatekeeper-bot` (jo marzi)
   - **Region:** Singapore (South Asia ke liye best)
   - **Branch:** `main`
   - **Runtime:** `Docker`
   - **Build Command:** *(khali chhod do — Dockerfile se automatically)*
   - **Start Command:** *(khali chhod do — Dockerfile CMD use hoga)*

#### Step 3: Environment Variables Set karo

Render Dashboard → Environment tab mein:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `1234567890:ABCdef...` (BotFather se) |
| `OWNER_ID` | `987654321` (tumhari ID) |
| `OWNER_USERNAME` | `your_username` |
| `REQUEST_TIMEOUT` | `300` |

#### Step 4: Deploy!

- **Create Web Service** dabao
- Render automatically Docker image build karega aur deploy karega
- Logs mein `"Bot is running! Polling for updates..."` dikhega

> **⚠️ Important:** Render Free tier pe service 15 min inactivity ke baad sleep ho jaati hai.
> Bot ke liye **Paid plan** use karo (ya UptimeRobot se ping karte raho).

---

## 💻 Local Development

```bash
# Clone karo
git clone https://github.com/TUMHARA_USERNAME/gatekeeper-bot.git
cd gatekeeper-bot

# Virtual environment banao
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ya
venv\Scripts\activate     # Windows

# Dependencies install karo
pip install -r requirements.txt

# .env file banao
cp .env.example .env
# .env file edit karo aur apni values dalo

# Bot chalao
python bot.py
```

---

## 📋 Owner Commands (PM mein)

| Command | Kya karta hai |
|---------|---------------|
| `/start` | Bot start karo aur PM check karo |
| `/help` | Saare commands ki list |
| `/status` | Pending requests dekho |
| `/clearall` | Saari pending requests clear karo |

---

## 🔧 Supported Commands (Intercept hoti hain)

| Command | Action |
|---------|--------|
| `/ban` | User ko ban karo |
| `/unban` | User ko unban karo |
| `/kick` | User ko kick karo |
| `/mute` | User ko mute karo |
| `/unmute` | User ko unmute karo |
| `/purge` | Messages delete karo |
| `/pin` | Message pin karo |
| `/unpin` | Message unpin karo |
| `/promote` | User ko admin banao |
| `/demote` | Admin remove karo |
| `/warn` | Warning do |
| *Koi bhi custom command* | Owner se approve hogi |

---

## 🔄 Flow Diagram

```
Admin → /ban @user
         ↓
   [Message Delete]
         ↓
   Owner ko PM:
   "Hey Boss! Ye request..."
   [✅ Yes] [❌ No]
         ↓
   Owner presses Yes
         ↓
   Bot executes /ban in group
   + Admin ko notify
```

---

## 📝 Notes

- Bot ko group mein **Admin** hona ZAROORI hai
- Owner ki commands group mein directly work karti hain (intercept nahi hoti)
- Requests memory mein store hoti hain — bot restart pe clear ho jaati hain
- Future me database add kar sakte ho persistence ke liye
