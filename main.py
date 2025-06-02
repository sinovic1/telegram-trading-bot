import logging
import asyncio
import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os

# === CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc")
AUTHORIZED_USER_ID = 7469299312

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === SCHEDULER SETUP ===
scheduler = AsyncIOScheduler()

# === DELETE WEBHOOK ON START ===
async def delete_webhook():
    try:
        bot = telegram.Bot(BOT_TOKEN)
        await bot.delete_webhook()
        logger.info("✅ Webhook deleted.")
    except Exception as e:
        logger.error(f"❌ Failed to delete webhook: {e}")

# === /STATUS COMMAND ===
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == AUTHORIZED_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Everything is working fine.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🚫 Unauthorized.")

# === DUMMY STRATEGY CHECK ===
async def check_signals():
    logger.info("📊 Checking signals... (simulate signal logic here)")

# === MAIN FUNCTION ===
async def main():
    await delete_webhook()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("status", status_command))

    scheduler.add_job(check_signals, "interval", minutes=1)
    scheduler.start()

    logger.info("🤖 Bot started with polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

# === ENTRY POINT ===
loop = asyncio.get_event_loop()
loop.run_until_complete(main())

