import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# --- Settings ---
TOKEN = "7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc"
OWNER_ID = 7469299312

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Async functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text("🤖 Bot is running and ready!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text("✅ Everything is working fine.")

async def check_signals():
    try:
        logger.info("📊 Checking signals...")
        # Add your strategy logic here
        # await application.bot.send_message(chat_id=OWNER_ID, text="📈 New signal!")
    except Exception as e:
        logger.error(f"⚠️ Error in signal check: {e}")
        await application.bot.send_message(chat_id=OWNER_ID, text="⚠️ Bot signal loop crashed!")

# --- App and Scheduler ---
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))

scheduler = AsyncIOScheduler()
scheduler.add_job(check_signals, "interval", seconds=30)
scheduler.start()

# --- Start polling ---
if __name__ == "__main__":
    logger.info("🤖 Bot started with polling...")
    application.run_polling()


