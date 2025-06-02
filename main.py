import logging
import pytz
import asyncio
import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# === BOT CONFIG ===
BOT_TOKEN = '7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc'
OWNER_ID = 7469299312

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === STRATEGY PLACEHOLDER ===
def generate_signal():
    return {
        "pair": "EUR/USD",
        "entry": 1.0850,
        "tp1": 1.0870,
        "tp2": 1.0890,
        "tp3": 1.0910,
        "sl": 1.0820
    }

# === STATUS CHECK ===
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Bot is running fine.")

# === SIGNAL SENDER ===
async def check_signals():
    try:
        signal = generate_signal()
        text = (
            f"📉 *New Signal Detected!*\n\n"
            f"*Pair:* {signal['pair']}\n"
            f"*Entry:* {signal['entry']}\n"
            f"*TP1:* {signal['tp1']}\n"
            f"*TP2:* {signal['tp2']}\n"
            f"*TP3:* {signal['tp3']}\n"
            f"*SL:* {signal['sl']}"
        )
        await application.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending signal: {e}")
        await application.bot.send_message(chat_id=OWNER_ID, text=f"⚠️ Error: {e}")

# === MAIN FUNCTION ===
async def main():
    global application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Force delete any existing webhook to avoid conflict
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete webhook: {e}")

    # Add handlers
    application.add_handler(CommandHandler("status", status))

    # Start scheduled jobs
    scheduler = AsyncIOScheduler(timezone=pytz.utc)
    scheduler.add_job(check_signals, IntervalTrigger(minutes=15))
    scheduler.start()

    # Run polling
    logger.info("🤖 Bot started with polling...")
    await application.run_polling()

# === ENTRY POINT ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

