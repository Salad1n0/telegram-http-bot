import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text.startswith("http"):
        await update.message.reply_text("Надішли URL для GET-запиту")
        return

    try:
        r = requests.get(text, timeout=10)
        await update.message.reply_text(
            f"Status: {r.status_code}\n\n{r.text[:4000]}"
        )
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()