import os
import json
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---- СТАНИ ----
STATE_NONE = 0
STATE_URL = 1
STATE_METHOD = 2
STATE_AUTH = 3
STATE_BODY = 4

user_state = {}
user_data = {}

# ---- /start ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_user.id] = STATE_URL
    user_data[update.effective_user.id] = {}

    await update.message.reply_text(
        "👋 Надішли URL для HTTP-запиту"
    )

# ---- ОБРОБКА ТЕКСТУ ----
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    state = user_state.get(uid, STATE_NONE)

    # URL
    if state == STATE_URL:
        user_data[uid]["url"] = text
        user_state[uid] = STATE_METHOD

        keyboard = [
            [
                InlineKeyboardButton("GET", callback_data="METHOD_GET"),
                InlineKeyboardButton("POST", callback_data="METHOD_POST"),
            ]
        ]
        await update.message.reply_text(
            "Обери метод:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # BODY
    elif state == STATE_BODY:
        try:
            body = json.loads(text)
            user_data[uid]["body"] = body
        except Exception:
            await update.message.reply_text(
                "❌ Невалідний JSON.\n"
                "Спробуй ще раз або напиши /start"
            )
            return

        await perform_request(update, context, uid)

# ---- КНОПКИ ----
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    data = query.data

    # METHOD
    if data.startswith("METHOD_"):
        method = data.replace("METHOD_", "")
        user_data[uid]["method"] = method

        user_state[uid] = STATE_AUTH
        keyboard = [
            [
                InlineKeyboardButton("🔐 З токеном", callback_data="AUTH_YES"),
                InlineKeyboardButton("🔓 Без токена", callback_data="AUTH_NO"),
            ]
        ]
        await query.edit_message_text(
            "Авторизація:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # AUTH
    elif data == "AUTH_YES":
        user_data[uid]["auth"] = True
        user_state[uid] = STATE_BODY
        await query.edit_message_text(
            "Надішли JSON body:"
        )

    elif data == "AUTH_NO":
        user_data[uid]["auth"] = False
        user_data[uid]["body"] = None
        await perform_request(query, context, uid)

# ---- HTTP ----
async def perform_request(source, context, uid):
    data = user_data[uid]

    headers = {}
    if data.get("auth"):
        headers["Authorization"] = "Bearer YOUR_TOKEN_HERE"

    try:
        if data["method"] == "GET":
            r = requests.get(data["url"], headers=headers, timeout=15)
        else:
            r = requests.post(
                data["url"],
                headers=headers,
                json=data.get("body"),
                timeout=15,
            )

        text = (
            f"✅ Status: {r.status_code}\n\n"
            f"{r.text[:3500]}"
        )

    except Exception as e:
        text = f"❌ Помилка:\n{e}"

    user_state[uid] = STATE_URL
    user_data[uid] = {}

    if hasattr(source, "edit_message_text"):
        await source.edit_message_text(text)
    else:
        await source.message.reply_text(text)

    await context.bot.send_message(
        chat_id=uid,
        text="🔁 Можеш надсилати новий URL або /start",
    )

# ---- MAIN ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
