import os
import json
import requests
from flask import Flask, request

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# ---- простий state в памʼяті ----
user_state = {}
user_data = {}

STATE_URL = "url"
STATE_METHOD = "method"
STATE_AUTH = "auth"
STATE_TOKEN = "token"
STATE_JSON = "json"


# ---------- helpers ----------

def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=payload,
        timeout=10
    )


def edit_message(chat_id, message_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(
        f"{TELEGRAM_API}/editMessageText",
        json=payload,
        timeout=10
    )


def main_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "🌐 GET", "callback_data": "METHOD_GET"},
                {"text": "📦 POST", "callback_data": "METHOD_POST"}
            ]
        ]
    }


def auth_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "🔐 З авторизацією", "callback_data": "AUTH_YES"},
                {"text": "🔓 Без авторизації", "callback_data": "AUTH_NO"}
            ]
        ]
    }


def again_menu():
    return {
        "inline_keyboard": [
            [{"text": "🔁 Новий запит", "callback_data": "RESTART"}]
        ]
    }


# ---------- routes ----------

@app.route("/", methods=["GET"])
def health():
    return "alive"


@app.route("/", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    # ---- callback кнопок ----
    if "callback_query" in data:
        cq = data["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        action = cq["data"]

        if action == "METHOD_GET":
            user_data[chat_id]["method"] = "GET"
            user_state[chat_id] = STATE_AUTH
            edit_message(chat_id, message_id, "Авторизація?", auth_menu())

        elif action == "METHOD_POST":
            user_data[chat_id]["method"] = "POST"
            user_state[chat_id] = STATE_AUTH
            edit_message(chat_id, message_id, "Авторизація?", auth_menu())

        elif action == "AUTH_YES":
            user_state[chat_id] = STATE_TOKEN
            edit_message(chat_id, message_id, "🔑 Надішли токен (Bearer)")

        elif action == "AUTH_NO":
            user_data[chat_id]["token"] = None
            if user_data[chat_id]["method"] == "POST":
                user_state[chat_id] = STATE_JSON
                edit_message(chat_id, message_id, "📦 Надішли JSON")
            else:
                perform_request(chat_id)

        elif action == "RESTART":
            user_state[chat_id] = STATE_URL
            user_data[chat_id] = {}
            send_message(chat_id, "🌐 Надішли URL")

        return "ok"

    # ---- текстові повідомлення ----
    message = data.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # /start
    if text == "/start":
        user_state[chat_id] = STATE_URL
        user_data[chat_id] = {}
        send_message(chat_id, "👋 Надішли URL")
        return "ok"

    state = user_state.get(chat_id)

    # URL
    if state == STATE_URL:
        user_data[chat_id]["url"] = text
        user_state[chat_id] = STATE_METHOD
        send_message(chat_id, "Обери метод:", main_menu())

    # TOKEN
    elif state == STATE_TOKEN:
        user_data[chat_id]["token"] = text
        if user_data[chat_id]["method"] == "POST":
            user_state[chat_id] = STATE_JSON
            send_message(chat_id, "📦 Надішли JSON")
        else:
            perform_request(chat_id)

    # JSON
    elif state == STATE_JSON:
        try:
            user_data[chat_id]["json"] = json.loads(text)
        except Exception:
            send_message(
                chat_id,
                "❌ Невалідний JSON\nСпробуй ще раз або /start"
            )
            return "ok"

        perform_request(chat_id)

    return "ok"


# ---------- request executor ----------

def perform_request(chat_id):
    data = user_data.get(chat_id, {})
    headers = {}

    if data.get("token"):
        headers["Authorization"] = f"Bearer {data['token']}"

    try:
        if data["method"] == "GET":
            r = requests.get(data["url"], headers=headers, timeout=15)
        else:
            r = requests.post(
                data["url"],
                headers=headers,
                json=data.get("json"),
                timeout=15
            )

        result_text = (
            f"✅ Status: {r.status_code}\n\n"
            f"{r.text[:3500]}"
        )

    except Exception as e:
        result_text = f"❌ Помилка:\n{str(e)}"

    # 1️⃣ РЕЗУЛЬТАТ — ОКРЕМЕ ПОВІДОМЛЕННЯ
    send_message(chat_id, result_text)

    # 2️⃣ КНОПКА — ОКРЕМЕ ПОВІДОМЛЕННЯ
    send_message(chat_id, "Що робимо далі?", again_menu())

    user_state[chat_id] = None
    user_data[chat_id] = {}


# ---------- entrypoint ----------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
