import os
import requests
from flask import Flask, request

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# --- HEALTH CHECK (GET) ---
@app.route("/", methods=["GET"])
def health():
    return "alive"

# --- TELEGRAM WEBHOOK (POST) ---
@app.route("/", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    # Telegram може надсилати різні типи апдейтів
    message = data.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
        send_message(
            chat_id,
            "✅ Бот працює!\n\n"
            "Надішли будь-який URL, і я зроблю GET-запит."
        )
    else:
        # Пробуємо зробити GET-запит
        try:
            r = requests.get(text, timeout=10)
            send_message(
                chat_id,
                f"🌐 URL: {text}\n"
                f"✅ Status: {r.status_code}\n\n"
                f"{r.text[:3500]}"
            )
        except Exception as e:
            send_message(
                chat_id,
                f"❌ Помилка запиту:\n{str(e)}"
            )

    return "ok"

# --- SEND MESSAGE ---
def send_message(chat_id: int, text: str):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        },
        timeout=10
    )

# --- ENTRYPOINT ---
if __name__ == "__main__":
    # Render сам підставляє PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
