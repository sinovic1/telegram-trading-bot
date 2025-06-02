import os
import logging
import pytz
import requests
import pandas as pd
import ta
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

# === CONFIG ===
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = 7469299312
PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD']
TIMEZONE = utc

# === LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === ANALYSIS STRATEGIES ===
def fetch_data(pair):
    url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={pair[:3]}&to_symbol={pair[3:]}&interval=15min&apikey=demo"
    r = requests.get(url)
    data = r.json()
    try:
        df = pd.DataFrame.from_dict(data['Time Series FX (15min)'], orient='index', dtype=float)
        df.columns = ['open', 'high', 'low', 'close']
        df.sort_index(inplace=True)
        return df
    except:
        return None

def analyze(df):
    signals = []

    # Indicators
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    df['ema'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    bb = ta.volatility.BollingerBands(df['close'])
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()

    last = df.iloc[-1]

    # Strategy Agreement Counter
    count = 0

    # RSI
    if last['rsi'] < 30:
        count += 1
        signals.append("📉 RSI: OVERSOLD")
    elif last['rsi'] > 70:
        count += 1
        signals.append("📈 RSI: OVERBOUGHT")

    # EMA
    if last['close'] > last['ema']:
        count += 1
        signals.append("📈 Price > EMA")
    else:
        signals.append("📉 Price < EMA")

    # MACD
    if last['macd'] > last['macd_signal']:
        count += 1
        signals.append("📈 MACD Crossover")
    else:
        signals.append("📉 MACD Bearish")

    # Bollinger Bands
    if last['close'] < last['bb_lower']:
        count += 1
        signals.append("📉 Below Lower BB")
    elif last['close'] > last['bb_upper']:
        count += 1
        signals.append("📈 Above Upper BB")

    return count, signals, last['close']

def generate_signal(pair):
    df = fetch_data(pair)
    if df is None or len(df) < 30:
        return None

    count, signals, price = analyze(df)

    if count >= 2:
        tp1 = round(price * 1.002, 5)
        tp2 = round(price * 1.004, 5)
        tp3 = round(price * 1.006, 5)
        sl = round(price * 0.996, 5)
        return f"🔔 Signal for {pair}:\nPrice: {price}\n" + "\n".join(signals) + f"\n🎯 TP1: {tp1}\n🎯 TP2: {tp2}\n🎯 TP3: {tp3}\n🛑 SL: {sl}"
    return None

# === TELEGRAM BOT ===
bot = Bot(token=TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ALLOWED_USER_ID:
        await update.message.reply_text("✅ Bot is running.")
    else:
        await update.message.reply_text("⛔️ Not authorized.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ALLOWED_USER_ID:
        await update.message.reply_text("✅ Everything is working fine.")
    else:
        await update.message.reply_text("⛔️ Not authorized.")

async def warn_user():
    await bot.send_message(chat_id=ALLOWED_USER_ID, text="⚠️ Warning: Signal loop has stopped!")

# === SCHEDULER LOOP ===
def check_signals():
    try:
        for pair in PAIRS:
            signal = generate_signal(pair)
            if signal:
                bot.send_message(chat_id=ALLOWED_USER_ID, text=signal)
    except Exception as e:
        logger.error(f"Signal loop error: {e}")
        try:
            bot.send_message(chat_id=ALLOWED_USER_ID, text=f"⚠️ Error in signal loop:\n{e}")
        except:
            pass

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(check_signals, 'interval', minutes=15)
    scheduler.start()

    logger.info("Scheduler started")
    app.run_polling()

if __name__ == "__main__":
    main()
