# main.py
import logging
import asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import random

# Constants
TOKEN = "7923000946:AAEx8TZsaIl6GL7XUwPGEM6a6-mBNfKwUz8"
OWNER_ID = 7469299312
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulated strategy checkers (replace with real logic)
def check_rsi(pair): return random.choice([True, False])
def check_macd(pair): return random.choice([True, False])
def check_ema(pair): return random.choice([True, False])
def check_bollinger(pair): return random.choice([True, False])

# Signal checker
async def check_signals(application):
    for pair in PAIRS:
        rsi = check_rsi(pair)
        macd = check_macd(pair)
        ema = check_ema(pair)
        boll = check_bollinger(pair)

        true_count = sum([rsi, macd, ema, boll])
        if true_count >= 2:
            entry = round(random.uniform(1.0, 1.5), 4)
            tp1 = round(entry + 0.0020, 4)
            tp2 = round(entry + 0.0040, 4)
            tp3 = round(entry + 0.0060, 4)
            sl = round(entry - 0.0030, 4)
            message = (
                f"📈 Signal for {pair}\n"
                f"Entry: {entry}\n"
                f"Take Profit 1: {tp1}\n"
                f"Take Profit 2: {tp2}\n"
                f"Take Profit 3: {tp3}\n"
                f"Stop Loss: {sl}"
            )
            await application.bot.send_message(chat_id=OWNER_ID, text=message)

# /status command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text("✅ Bot is running and active.")

# Crash alert
def setup_crash_handler(application):
    def handle_exception(loop, context):
        msg = f"❌ Bot crashed: {context.get('exception') or context['message']}"
        asyncio.create_task(application.bot.send_message(chat_id=OWNER_ID, text=msg))
        loop.default_exception_handler(context)
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

# Main async function
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("status", status))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_signals, "interval", seconds=60, args=[app])
    scheduler.start()

    setup_crash_handler(app)
    logger.info("🤖 Bot started with polling...")
    await app.bot.delete_webhook()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())


