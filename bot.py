import os
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔓 Без авторизації", callback_data="auth_none")],
        [InlineKeyboardButton("🔐 З авторизацією", callback_data="auth_bearer")]
    ]
    await update.message.reply_text(
        "Оберіть тип відправки запиту:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- AUTH SELECT ----------
async def auth_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["auth"] = query.data.replace("auth_", "")

    keyboard = [
        [
            InlineKeyboardButton("📥 GET", callback_data="method_GET"),
            InlineKeyboardButton("📤 POST", callback_data="method_POST")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_auth")]
    ]

    await query.edit_message_text(
        "Оберіть HTTP-метод:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- METHOD SELECT ----------
async def method_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["method"] = query.data.replace("method_", "")

    if context.user_data["auth"] == "bearer":
        await query.edit_message_text("🔐 Надішліть Bearer token:")
    else:
        await query.edit_message_text("🌐 Надішліть URL:")

# ---------- BACK ----------
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)

# ---------- MESSAGE HANDLER ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # token
    if context.user_data.get("auth") == "bearer" and "token" not in context.user_data:
        context.user_data["token"] = text
        await update.message.reply_text("🌐 Тепер надішліть URL:")
        return

    # url
    if "url" not in context.user_data:
        context.user_data["url"] = text

        if context.user_data["method"] == "POST":
            await update.message.reply_text("📦 Надішліть JSON body:")
        else:
            await send_request(update, context)
        return

    # body
    if context.user_data["method"] == "POST":
        context.user_data["body"] = text
        await send_request(update, context)

# ---------- REQUEST ----------
async def send_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data["url"]
    method = context.user_data["method"]
    headers = {}

    if context.user_data.get("auth") == "bearer":
        headers["Authorization"] = f"Bearer {context.user_data['token']}"

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, headers=headers, json=eval(context.user_data["body"]), timeout=10)

        await update.message.reply_text(
            f"✅ Status: {r.status_code}\n\n{r.text[:3500]}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

    context.user_data.clear()

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(auth_select, pattern="^auth_"))
    app.add_handler(CallbackQueryHandler(method_select, pattern="^method_"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
