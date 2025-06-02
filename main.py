from keep_alive import keep_alive
import os
import time
import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# --- ENV ---
BOT_TOKEN = os.environ['BOT_TOKEN']
AUTHORIZED_USER = int(os.environ['AUTHORIZED_USER'])

# --- START ---
keep_alive()
bot = Bot(token=BOT_TOKEN)
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# --- PAIRS ---
PAIRS = {
    'EURUSD=X': 'EUR/USD',
    'GBPUSD=X': 'GBP/USD',
    'USDJPY=X': 'USD/JPY',
    'USDCHF=X': 'USD/CHF',
    'AUDUSD=X': 'AUD/USD',
    'USDCAD=X': 'USD/CAD',
    'EURJPY=X': 'EUR/JPY',
    'GBPJPY=X': 'GBP/JPY',
    'EURGBP=X': 'EUR/GBP',
    'AUDJPY=X': 'AUD/JPY',
    'NZDUSD=X': 'NZD/USD',
    'NZDJPY=X': 'NZD/JPY'
}

# --- TRACKERS ---
active_signals = {}  # {symbol: {entry, tp1/2/3, sl, direction, message_id}}
signal_stats = {}  # {symbol: {'win': 0, 'loss': 0, 'total': 0}}

last_signal_time = {}


def calculate_score(reasons):
    score = 0
    for r in reasons:
        if "FVG" in r or "ICT" in r:
            score += 2
        else:
            score += 1
    return score


def get_15m_trend(symbol):
    df = yf.download(tickers=symbol,
                     interval='15m',
                     period='1d',
                     progress=False)
    df.columns = [
        col[0].lower() if isinstance(col, tuple) else col.lower()
        for col in df.columns
    ]
    if 'close' not in df.columns: return None
    df['ema'] = EMAIndicator(df['close'], window=20).ema_indicator()
    return "bullish" if df.iloc[-1]['close'] > df.iloc[-1]['ema'] else "bearish"


def check_ict_logic(df):
    last, prev = df.iloc[-1], df.iloc[-2]
    if last['low'] < prev['low'] and last['close'] > prev['close']:
        return "ICT Liquidity Sweep Buy"
    if last['high'] > prev['high'] and last['close'] < prev['close']:
        return "ICT Liquidity Sweep Sell"
    return None


def check_fvg(df):
    if len(df) < 3: return None
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    if c2['low'] > c1['high'] and c3['low'] > c1['high']:
        return "FVG Buy"
    if c2['high'] < c1['low'] and c3['high'] < c1['low']:
        return "FVG Sell"
    return None


def get_order_block(df, direction="buy", window=10):
    for i in range(-window, -1):
        c = df.iloc[i]
        next_c = df.iloc[i + 1]
        if direction == "buy" and c['close'] < c['open'] and next_c[
                'close'] > c['high']:
            return c['open'], c['close']
        elif direction == "sell" and c['close'] > c['open'] and next_c[
                'close'] < c['low']:
            return c['open'], c['close']
    return None, None


def check_signals(symbol):
    now = datetime.utcnow()
    if now.hour < 7 or now.hour > 22:
        return None

    df = yf.download(tickers=symbol,
                     interval='5m',
                     period='1d',
                     progress=False)
    df.columns = [
        col[0].lower() if isinstance(col, tuple) else col.lower()
        for col in df.columns
    ]
    if df.empty or 'close' not in df.columns or len(df) < 50:
        return None

    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
    df['ema'] = EMAIndicator(df['close'], window=20).ema_indicator()
    df['macd'] = MACD(df['close']).macd_diff()
    bb = BollingerBands(df['close'])
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    latest = df.iloc[-1]
    price = round(latest['close'], 5)

    trend = get_15m_trend(symbol)
    if trend is None:
        return None

    for direction in ['buy', 'sell']:
        is_buy = direction == 'buy'
        if (trend == 'bullish' and is_buy) or (trend == 'bearish'
                                               and not is_buy):
            reasons = []

            # Add logic-based reasons
            ict = check_ict_logic(df)
            fvg = check_fvg(df)
            if ict and direction.capitalize() in ict: reasons.append(ict)
            if fvg and direction.capitalize() in fvg: reasons.append(fvg)
            if is_buy and latest['rsi'] < 30: reasons.append("RSI Buy")
            if not is_buy and latest['rsi'] > 70: reasons.append("RSI Sell")
            if is_buy and latest['close'] > latest['ema']:
                reasons.append("EMA Buy")
            if not is_buy and latest['close'] < latest['ema']:
                reasons.append("EMA Sell")
            if is_buy and latest['macd'] > 0: reasons.append("MACD Buy")
            if not is_buy and latest['macd'] < 0: reasons.append("MACD Sell")
            if is_buy and latest['close'] < latest['bb_lower']:
                reasons.append("Bollinger Buy")
            if not is_buy and latest['close'] > latest['bb_upper']:
                reasons.append("Bollinger Sell")

            score = calculate_score(reasons)

            # Count how many core indicators agree
            core_signals = ['RSI', 'EMA', 'MACD', 'Bollinger']
            core_hits = sum(1 for cs in core_signals
                            if any(cs in r for r in reasons))
            print(
                f"{PAIRS[symbol]} [{direction.upper()}] reasons: {reasons}, score: {score}, core_hits: {core_hits}"
            )

            if core_hits < 3:
                return None
            if score < 2:
                return None

            if symbol in last_signal_time and now - last_signal_time[
                    symbol] < timedelta(minutes=30):
                return None
            last_signal_time[symbol] = now

            step = 0.01 if "JPY" in PAIRS[symbol] else 0.0010
            tp = round(
                price +
                step, 3 if "JPY" in PAIRS[symbol] else 5) if is_buy else round(
                    price - step, 3 if "JPY" in PAIRS[symbol] else 5)
            emoji = "🟢" if is_buy else "🔴"

            msg = (f"{emoji} *{PAIRS[symbol]} {direction.upper()} Signal*\n"
                   f"Indicators: {', '.join(reasons)}\n\n"
                   f"*Entry:* `{price}`\n"
                   f"*TP:* `{tp}`")

            bot.send_message(chat_id=AUTHORIZED_USER,
                             text=msg,
                             parse_mode="Markdown")
    return None


def check_tp_sl():
    for symbol, data in list(active_signals.items()):
        df = yf.download(tickers=symbol,
                         interval='5m',
                         period='1d',
                         progress=False)
        if df.empty or 'close' not in df.columns: continue
        latest_price = df['close'].iloc[-1]

        is_buy = data['is_buy']
        hit = None

        if is_buy:
            if latest_price >= data['tp3']:
                hit = "TP3 ✅"
                signal_stats[symbol]['win'] += 1
            elif latest_price >= data['tp2']:
                hit = "TP2 ✅"
                signal_stats[symbol]['win'] += 1
            elif latest_price >= data['tp1']:
                hit = "TP1 ✅"
                signal_stats[symbol]['win'] += 1
            elif latest_price <= data['sl']:
                hit = "SL ❌"
                signal_stats[symbol]['loss'] += 1
        else:
            if latest_price <= data['tp3']:
                hit = "TP3 ✅"
                signal_stats[symbol]['win'] += 1
            elif latest_price <= data['tp2']:
                hit = "TP2 ✅"
                signal_stats[symbol]['win'] += 1
            elif latest_price <= data['tp1']:
                hit = "TP1 ✅"
                signal_stats[symbol]['win'] += 1
            elif latest_price >= data['sl']:
                hit = "SL ❌"
                signal_stats[symbol]['loss'] += 1

        if hit:
            bot.edit_message_text(
                chat_id=AUTHORIZED_USER,
                message_id=data['msg_id'],
                text=f"✅ *RESULT: {hit}*\n\n" +
                f"*Entry:* `{data['entry']}`\n" + f"*TP1:* `{data['tp1']}`\n" +
                f"*TP2:* `{data['tp2']}`\n" + f"*TP3:* `{data['tp3']}`\n" +
                f"*SL:* `{data['sl']}`",
                parse_mode="Markdown")
            del active_signals[symbol]


def send_weekly_report():
    lines = ["📅 *Weekly Report Summary*\n"]
    total_signals = total_wins = total_losses = 0
    top_pair = ""
    top_rate = 0

    for symbol, stats in signal_stats.items():
        wins = stats['win']
        losses = stats['loss']
        total = stats['total']
        win_rate = (wins / total) * 100 if total else 0
        total_signals += total
        total_wins += wins
        total_losses += losses

        lines.append(
            f"*{PAIRS[symbol]}*: {total} signals — {wins} ✅ / {losses} ❌ ({win_rate:.1f}%)"
        )

        if win_rate > top_rate:
            top_rate = win_rate
            top_pair = PAIRS[symbol]

    if total_signals == 0:
        lines.append("\nNo signals sent this week.")
    else:
        overall = (total_wins / total_signals) * 100
        lines.append(f"\n*Overall Win Rate:* {overall:.1f}%")
        lines.append(f"*Top Performer:* {top_pair} ({top_rate:.1f}%)")

    report = "\n".join(lines)
    bot.send_message(chat_id=AUTHORIZED_USER,
                     text=report,
                     parse_mode="Markdown")


# Command handlers
def start(update: Update, context: CallbackContext):
    if update.effective_user.id == AUTHORIZED_USER:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="🤖 Bot is running!")


def status(update: Update, context: CallbackContext):
    if update.effective_user.id == AUTHORIZED_USER:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="✅ Everything is working fine.")


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("status", status))


# Main signal + TP check loop
def signal_loop():
    print("✅ Signal loop has started!")
    while True:
        for symbol in PAIRS:
            try:
                check_signals(symbol)
            except Exception as e:
                logging.error(f"Signal error {symbol}: {e}")
        check_tp_sl()
        time.sleep(300)


# Scheduler for weekly report
scheduler = BackgroundScheduler()
from pytz import utc  # add at the top of your file if not already

scheduler.add_job(send_weekly_report,
                  'cron',
                  day_of_week='sun',
                  hour=21,
                  minute=0,
                  timezone=utc)

scheduler.start()

# Start the bot
updater.start_polling()
signal_loop()
