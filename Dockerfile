# ─── GateKeeper Bot — Dockerfile ─────────────────────────────────────────────
# Python 3.11 slim image use karo (chhota aur fast)
FROM python:3.11-slim

# Working directory set karo
WORKDIR /app

# Pehle requirements copy karo (Docker cache optimization)
COPY requirements.txt .

# Dependencies install karo
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baaki saare files copy karo
COPY . .

# Non-root user banao (security best practice)
RUN adduser --disabled-password --gecos '' botuser && \
    chown -R botuser:botuser /app
USER botuser

# Bot start karo
CMD ["python", "-u", "bot.py"]
