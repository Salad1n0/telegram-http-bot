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
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# =====================
# USER STATE (simple FSM)
# =====================
STATE = {}

STEP_AUTH = "auth"
STEP_TOKEN = "token"
STEP_METHOD = "method"
STEP_URL = "url"
STEP_JSON = "json"

# =====================
# MENUS
# =====================
def menu_auth():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 Без авторизації", callback_data="auth_no")],
        [InlineKeyboardButton("🔐 З авторизацією", callback_data="auth_yes")],
    ])

def menu_method():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("GET", callback_data="method_get")],
        [InlineKeyboardButton("POST", callback_data="method_post")],
    ])

def menu_again():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Новий запит", callback_data="restart")]
    ])

# =====================
# START
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    STATE[uid] = {"step": STEP_AUTH}

    await update.message.reply_text(
        "🐒 HTTP Monkey\n\n"
        "Обери режим запиту:",
        reply_markup=menu_auth()
    )

# =====================
# CALLBACKS
# =====================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data == "restart":
        STATE[uid] = {"step": STEP_AUTH}
        await query.message.reply_text(
            "🔄 Почнемо знову\nОбери режим:",
            reply_markup=menu_auth()
        )
        return

    if data.startswith("auth_"):
        STATE[uid]["auth"] = (data == "auth_yes")

        if STATE[uid]["auth"]:
            STATE[uid]["step"] = STEP_TOKEN
            await query.message.reply_text(
                "🔐 Введи токен авторизації\n"
                "(буде використано як Bearer token)"
            )
        else:
            STATE[uid]["step"] = STEP_METHOD
            await query.message.reply_text(
                "Обери HTTP метод:",
                reply_markup=menu_method()
            )
        return

    if data.startswith("method_"):
        STATE[uid]["method"] = data.replace("method_", "").upper()
        STATE[uid]["step"] = STEP_URL

        await query.message.reply_text("🌐 Надішли URL:")
        return

# =====================
# TEXT HANDLER
# =====================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    state = STATE.get(uid)

    if not state:
        await update.message.reply_text("Натисни /start")
        return

    # TOKEN
    if state["step"] == STEP_TOKEN:
        state["token"] = text
        state["step"] = STEP_METHOD
        await update.message.reply_text(
            "Обери HTTP метод:",
            reply_markup=menu_method()
        )
        return

    # URL
    if state["step"] == STEP_URL:
        state["url"] = text

        if state["method"] == "POST":
            state["step"] = STEP_JSON
            await update.message.reply_text(
                "📦 Надішли JSON body\n"
                "(можна з відступами)"
            )
        else:
            await execute_request(update, uid)
        return

    # JSON
    if state["step"] == STEP_JSON:
        try:
            state["json"] = json.loads(text)
        except json.JSONDecodeError as e:
            await update.message.reply_text(
                f"❌ Невалідний JSON:\n`{e}`",
                parse_mode="Markdown",
                reply_markup=menu_again()
            )
            return

        await execute_request(update, uid)
        return

# =====================
# EXECUTE REQUEST
# =====================
async def execute_request(update: Update, uid: int):
    state = STATE[uid]

    headers = {}
    if state.get("auth"):
        headers["Authorization"] = f"Bearer {state.get('token')}"

    try:
        if state["method"] == "GET":
            r = requests.get(state["url"], headers=headers, timeout=15)
        else:
            r = requests.post(
                state["url"],
                headers={**headers, "Content-Type": "application/json"},
                json=state.get("json"),
                timeout=15
            )

        body = r.text[:4000]

        await update.message.reply_text(
            f"✅ Status: {r.status_code}\n\n{body}",
            reply_markup=menu_again()
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Помилка запиту:\n{e}",
            reply_markup=menu_again()
        )

    STATE[uid]["step"] = None

# =====================
# MAIN
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("🤖 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
