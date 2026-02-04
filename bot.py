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


# ───────────────────── START ─────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        [
            InlineKeyboardButton("🔓 Без авторизації", callback_data="auth_no"),
            InlineKeyboardButton("🔐 З авторизацією", callback_data="auth_yes"),
        ]
    ]

    await update.message.reply_text(
        "Обери режим авторизації:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ───────────────────── AUTH ─────────────────────
async def choose_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "auth_yes":
        context.user_data["auth"] = True
        await query.edit_message_text("🔐 Надішли токен (без `Bearer`):")

    else:
        context.user_data["auth"] = False
        await show_method_menu(query)


async def save_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["token"] = update.message.text.strip()
    await show_method_menu(update)


# ───────────────────── METHOD ─────────────────────
async def show_method_menu(target):
    keyboard = [
        [
            InlineKeyboardButton("GET", callback_data="method_get"),
            InlineKeyboardButton("POST", callback_data="method_post"),
        ]
    ]

    await target.message.reply_text(
        "Обери HTTP метод:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def choose_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    method = query.data.replace("method_", "").upper()
    context.user_data["method"] = method

    await query.edit_message_text(
        f"➡️ Надішли URL для {method}-запиту:"
    )


# ───────────────────── URL & BODY ─────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "url" not in context.user_data:
        context.user_data["url"] = update.message.text.strip()

        if context.user_data["method"] == "POST":
            await update.message.reply_text(
                "📦 Надішли JSON тіло (або `{}`):"
            )
        else:
            await send_request(update, context)

    else:
        try:
            context.user_data["body"] = json.loads(update.message.text)
        except json.JSONDecodeError:
            await update.message.reply_text("❌ Невалідний JSON")
            return

        await send_request(update, context)


# ───────────────────── REQUEST ─────────────────────
async def send_request(update_or_query, context):
    data = context.user_data

    headers = {}
    if data.get("auth"):
        headers["Authorization"] = f"Bearer {data.get('token')}"

    try:
        r = requests.request(
            method=data["method"],
            url=data["url"],
            headers=headers,
            json=data.get("body"),
            timeout=15,
        )

        text = r.text[:3500]

        if hasattr(update_or_query, "message"):
            await update_or_query.message.reply_text(
                f"✅ Status: {r.status_code}\n\n{text}"
            )
        else:
            await update_or_query.edit_message_text(
                f"✅ Status: {r.status_code}\n\n{text}"
            )

        await show_next_actions(update_or_query)

    except Exception as e:
        await update_or_query.message.reply_text(f"❌ Помилка: {e}")


# ───────────────────── AFTER ACTIONS ─────────────────────
async def show_next_actions(target):
    keyboard = [
        [
            InlineKeyboardButton("🔂 Повторити", callback_data="repeat"),
            InlineKeyboardButton("🔁 Новий запит", callback_data="new"),
        ]
    ]

    await target.message.reply_text(
        "Що робимо далі?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def post_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "repeat":
        await query.edit_message_text("🔂 Повторюю запит...")
        await send_request(query, context)

    elif query.data == "new":
        context.user_data.clear()
        await query.edit_message_text("🔁 Новий запит")
        await start(query, context)


# ───────────────────── MAIN ─────────────────────
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choose_auth, pattern="^auth_"))
    app.add_handler(CallbackQueryHandler(choose_method, pattern="^method_"))
    app.add_handler(CallbackQueryHandler(post_action, pattern="^(repeat|new)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
