import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --------- START ---------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔓 Без авторизації", callback_data="no_auth")],
        [InlineKeyboardButton("🔐 З авторизацією", callback_data="with_auth")]
    ]
    await update.message.reply_text(
        "Обери тип запиту:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --------- AUTH CHOICE ---------
async def auth_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["auth"] = query.data

    keyboard = [
        [InlineKeyboardButton("GET", callback_data="GET")],
        [InlineKeyboardButton("POST", callback_data="POST")]
    ]
    await query.edit_message_text(
        "Обери метод:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --------- METHOD CHOICE ---------
async def method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["method"] = query.data
    await query.edit_message_text("Надішли URL:")

# --------- HANDLE MESSAGE ---------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "url" not in context.user_data:
        context.user_data["url"] = text
        if context.user_data["method"] == "POST":
            await update.message.reply_text("Надішли JSON тіло:")
        else:
            await execute_request(update, context)
    else:
        context.user_data["body"] = text
        await execute_request(update, context)

# --------- EXECUTE REQUEST ---------
async def execute_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = context.user_data["method"]
    url = context.user_data["url"]
    auth = context.user_data["auth"]

    headers = {"Content-Type": "application/json"}

    if auth == "with_auth":
        token = context.user_data.get("token")
        if not token:
            await update.message.reply_text("Надішли токен:")
            context.user_data["awaiting_token"] = True
            return
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=20)
        else:
            body = context.user_data.get("body", "{}")
            data = json.loads(body)
            r = requests.post(url, headers=headers, json=data, timeout=20)

        await update.message.reply_text(
            f"✅ Status: {r.status_code}\n\n{r.text[:3500]}"
        )
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Невалідний JSON. Спробуй ще раз.")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

    context.user_data.clear()
    await update.message.reply_text("🔁 Можеш виконати новий запит /start")

# --------- TOKEN INPUT ---------
async def token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_token"):
        context.user_data["token"] = update.message.text.strip()
        context.user_data.pop("awaiting_token")
        await execute_request(update, context)

# --------- MAIN ---------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(auth_choice, pattern="^(no_auth|with_auth)$"))
    app.add_handler(CallbackQueryHandler(method_choice, pattern="^(GET|POST)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, token_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
