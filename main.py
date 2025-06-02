import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Your token
TOKEN = "7923000946:AAGkHu782eQXxhLF4IU1yNCyJO5ruXZhUtc"
OWNER_ID = 7469299312  # Your Telegram user ID

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = AsyncIOScheduler()

# Simple start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text("🤖 Bot is running and ready!")

# Status check
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text("✅ Everything is working fine.")

# Dummy signal checker
async def check_signals():
    try:
        logger.info("📈 Checking signals...")
        # Replace with real strategy
        # If a real signal is found:
        # await app.bot.send_message(chat_id=OWNER_ID, text="Signal here")
    except Exception as e:
        logger.error(f"Error in signal checking: {e}")
        await app.bot.send_message(chat_id=OWNER_ID, text="⚠️ Bot signal loop crashed!")

# Main async function
async def main():
    global app
    app = ApplicationBuilder().token(TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    # Schedule job every X seconds
    scheduler.add_job(check_signals, "interval", seconds=30)
    scheduler.start()

    logger.info("🤖 Bot started with polling...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())


