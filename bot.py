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

TOKEN = os.getenv("BOT_TOKEN")


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        [
            InlineKeyboardButton("🔐 З авторизацією", callback_data="auth_yes"),
            InlineKeyboardButton("🚫 Без авторизації", callback_data="auth_no"),
        ]
    ]

    await update.message.reply_text(
        "Обери режим авторизації:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- AUTH ----------
async def auth_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["auth"] = query.data == "auth_yes"

    if context.user_data["auth"]:
        await query.edit_message_text("🔐 Надішли Bearer токен:")
    else:
        context.user_data["token"] = None
        await ask_method(query, context)


# ---------- METHOD ----------
async def ask_method(update_or_query, context):
    keyboard = [
        [
            InlineKeyboardButton("GET", callback_data="method_get"),
            InlineKeyboardButton("POST", callback_data="method_post"),
        ]
    ]

    await update_or_query.edit_message_text(
        "Обери HTTP метод:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["method"] = query.data.replace("method_", "").upper()

    await query.edit_message_text(
        f"🌐 Надішли URL для {context.user_data['method']} запиту:"
    )


# ---------- MESSAGE HANDLER ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Bearer token
    if context.user_data.get("auth") and "token" not in context.user_data:
        context.user_data["token"] = text
        await ask_method(update.message, context)
        return

    # URL
    if "url" not in context.user_data:
        context.user_data["url"] = text

        if context.user_data["method"] == "POST":
            await update.message.reply_text(
                "📦 Надішли JSON тіло (`{}` якщо порожнє)\n\n"
                "⚠️ Усі строки мають бути в один рядок"
            )
        else:
            await send_request(update, context)
        return

    # JSON body
    try:
        context.user_data["body"] = json.loads(text)
        await send_request(update, context)

    except json.JSONDecodeError as e:
        keyboard = [
            [
                InlineKeyboardButton("🔁 Спробувати ще раз", callback_data="retry_json"),
                InlineKeyboardButton("🆕 Новий запит", callback_data="new"),
            ]
        ]

        await update.message.reply_text(
            f"❌ Невалідний JSON:\n`{e}`\n\n"
            "👉 Перевір лапки та переноси рядків",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )


# ---------- SEND REQUEST ----------
async def send_request(update_or_query, context):
    data = context.user_data

    headers = {}
    if data.get("token"):
        headers["Authorization"] = f"Bearer {data['token']}"

    try:
        if data["method"] == "GET":
            r = requests.get(data["url"], headers=headers, timeout=20)
        else:
            r = requests.post(
                data["url"],
                headers=headers,
                json=data.get("body"),
                timeout=20,
            )

        text = r.text
        if len(text) > 3500:
            text = text[:3500] + "\n... (truncated)"

        await update_or_query.message.reply_text(
            f"✅ Status: {r.status_code}\n\n{text}"
        )

    except Exception as e:
        await update_or_query.message.reply_text(f"❌ Помилка:\n{e}")

    await show_next_actions(update_or_query)


# ---------- NEXT ACTIONS ----------
async def show_next_actions(update_or_query):
    keyboard = [
        [
            InlineKeyboardButton("🔂 Повторити запит", callback_data="repeat"),
            InlineKeyboardButton("🔁 Новий запит", callback_data="new"),
        ]
    ]

    await update_or_query.message.reply_text(
        "Що робимо далі?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- POST ACTIONS ----------
async def post_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "repeat":
        await query.edit_message_text("🔂 Повторюю запит...")
        await send_request(query, context)

    elif query.data == "new":
        context.user_data.clear()
        await query.edit_message_text("🔁 Почнемо новий запит")
        await start(query, context)

    elif query.data == "retry_json":
        await query.edit_message_text("📦 Надішли JSON ще раз:")


# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(auth_choice, pattern="^auth_"))
    app.add_handler(CallbackQueryHandler(method_choice, pattern="^method_"))
    app.add_handler(CallbackQueryHandler(post_action))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
