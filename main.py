import logging
import time
import pandas as pd
import yfinance as yf
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# === SETTINGS ===
TELEGRAM_TOKEN = '7923000946:AAEx8TZsaIl6GL7XUwPGEM6a6-mBNfKwUz8'
ALLOWED_USER_ID = 7469299312
PAIR_LIST = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'USDCHF=X', 'AUDUSD=X', 'USDCAD=X']

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === STRATEGIES ===
def rsi_strategy(df):
    delta = df['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.rolling(14).mean()
    avg_loss = down.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    df['RSI'] = rsi
    return rsi.iloc[-1] < 30 or rsi.iloc[-1] > 70

def macd_strategy(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd.iloc[-1] > signal.iloc[-1] or macd.iloc[-1] < signal.iloc[-1]

def ema_strategy(df):
    ema50 = df['Close'].ewm(span=50).mean()
    ema200 = df['Close'].ewm(span=200).mean()
    return ema50.iloc[-1] > ema200.iloc[-1] or ema50.iloc[-1] < ema200.iloc[-1]

def bollinger_strategy(df):
    sma = df['Close'].rolling(20).mean()
    std = df['Close'].rolling(20).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return df['Close'].iloc[-1] < lower.iloc[-1] or df['Close'].iloc[-1] > upper.iloc[-1]

# === SIGNAL GENERATOR ===
def check_signals():
    bot = Bot(TELEGRAM_TOKEN)
    for symbol in PAIR_LIST:
        try:
            df = yf.download(symbol, period='7d', interval='1h')
            if df.empty:
                continue
            triggered = []
            if rsi_strategy(df): triggered.append('RSI')
            if macd_strategy(df): triggered.append('MACD')
            if ema_strategy(df): triggered.append('EMA')
            if bollinger_strategy(df): triggered.append('Bollinger')

            if len(triggered) >= 2:
                current_price = df['Close'].iloc[-1]
                tp1 = round(current_price * 1.002, 5)
                tp2 = round(current_price * 1.004, 5)
                tp3 = round(current_price * 1.006, 5)
                sl = round(current_price * 0.998, 5)
                message = (
                    f"📊 Signal for {symbol.replace('=X', '')}\n"
                    f"Triggered Strategies: {', '.join(triggered)}\n"
                    f"Entry: {current_price:.5f}\n"
                    f"🎯 TP1: {tp1}\n"
                    f"🎯 TP2: {tp2}\n"
                    f"🎯 TP3: {tp3}\n"
                    f"🛑 SL: {sl}"
                )
                bot.send_message(chat_id=ALLOWED_USER_ID, text=message)
        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")

# === COMMAND HANDLERS ===
def start(update: Update, context: CallbackContext):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    update.message.reply_text("🤖 Bot is running!")

def status(update: Update, context: CallbackContext):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    update.message.reply_text("✅ Everything is working fine.")

# === ERROR HANDLER ===
def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling update:", exc_info=context.error)

# === MAIN ===
def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", status))
    dp.add_error_handler(error_handler)

    # Run signal check every 15 minutes
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_signals, 'interval', minutes=15)
    scheduler.start()

    logger.info("Bot started. Polling...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
