import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("TradeSignalAI")

TOKEN = os.getenv("BOT_TOKEN")
UTC5 = timezone(timedelta(hours=5))

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
}

TIMEFRAMES = {
    "1 MIN": "1m",
    "5 MIN": "5m",
    "15 MIN": "15m",
    "30 MIN": "30m",
    "1 HOUR": "60m",
}

MAIN_MENU = ReplyKeyboardMarkup([
    ["📈 Live Signals", "🔥 Strongest Signal"],
    ["💱 Select Pair", "⏱ Select Time"],
    ["📊 Market Analysis", "📜 Signal History"],
    ["⚙️ Settings", "❓ Help"],
], resize_keyboard=True)

PAIR_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🇪🇺 EUR/USD", callback_data="pair:EUR/USD"),
        InlineKeyboardButton("🇬🇧 GBP/USD", callback_data="pair:GBP/USD"),
    ],
    [
        InlineKeyboardButton("🇯🇵 USD/JPY", callback_data="pair:USD/JPY"),
        InlineKeyboardButton("🇦🇺 AUD/USD", callback_data="pair:AUD/USD"),
    ],
    [
        InlineKeyboardButton("🇨🇦 USD/CAD", callback_data="pair:USD/CAD"),
        InlineKeyboardButton("🇨🇭 USD/CHF", callback_data="pair:USD/CHF"),
    ],
    [
        InlineKeyboardButton("🇳🇿 NZD/USD", callback_data="pair:NZD/USD"),
        InlineKeyboardButton("🇪🇺 EUR/GBP", callback_data="pair:EUR/GBP"),
    ],
    [
        InlineKeyboardButton("🇪🇺 EUR/JPY", callback_data="pair:EUR/JPY"),
        InlineKeyboardButton("🇬🇧 GBP/JPY", callback_data="pair:GBP/JPY"),
    ],
])

TIME_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("1 MIN", callback_data="time:1 MIN"),
        InlineKeyboardButton("5 MIN", callback_data="time:5 MIN"),
    ],
    [
        InlineKeyboardButton("15 MIN", callback_data="time:15 MIN"),
        InlineKeyboardButton("30 MIN", callback_data="time:30 MIN"),
    ],
    [InlineKeyboardButton("1 HOUR", callback_data="time:1 HOUR")],
])

def settings(context):
    context.user_data.setdefault("pair", "EUR/USD")
    context.user_data.setdefault("timeframe", "5 MIN")
    context.user_data.setdefault("history", [])
    return context.user_data

def fetch(symbol, interval):
    periods = {"1m": "1d", "5m": "5d", "15m": "5d", "30m": "5d", "60m": "1mo"}
    df = yf.download(
        symbol,
        period=periods.get(interval, "5d"),
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False,
    )

    if df is None or df.empty:
        raise ValueError("Market data is unavailable.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = pd.to_numeric(df["Close"], errors="coerce").dropna()

    if len(close) < 55:
        raise ValueError("Not enough candles for analysis.")

    return close

def analyze(pair, timeframe):
    close = fetch(PAIRS[pair], TIMEFRAMES[timeframe])

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, 1e-10)
    rsi = 100 - (100 / (1 + gain / loss))

    price = float(close.iloc[-1])
    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])
    rsi_value = float(rsi.iloc[-1])

    buy = 0
    sell = 0

    if e20 > e50:
        buy += 35
    else:
        sell += 35

    if price > e20:
        buy += 20
    else:
        sell += 20

    if 50 < rsi_value < 70:
        buy += 25
    elif 30 < rsi_value < 50:
        sell += 25
    elif rsi_value <= 30:
        buy += 15
    elif rsi_value >= 70:
        sell += 15

    momentum = float(close.iloc[-1] - close.iloc[-5])
    if momentum > 0:
        buy += 20
    elif momentum < 0:
        sell += 20

    if buy >= 60 and buy > sell:
        signal = "🟢 BUY"
        trend = "📈 UP TREND"
        confidence = min(95, buy)
    elif sell >= 60 and sell > buy:
        signal = "🔴 SELL"
        trend = "📉 DOWN TREND"
        confidence = min(95, sell)
    else:
        signal = "🟡 WAIT"
        trend = "↔️ SIDEWAYS"
        confidence = max(40, min(59, max(buy, sell)))

    strength_value = abs(e20 - e50) / max(abs(price), 1e-10) * 100000
    if strength_value < 5:
        strength = "🟡 WEAK"
    elif strength_value < 15:
        strength = "🟠 MEDIUM"
    else:
        strength = "🟢 STRONG"

    return {
        "pair": pair,
        "timeframe": timeframe,
        "price": price,
        "ema20": e20,
        "ema50": e50,
        "rsi": rsi_value,
        "signal": signal,
        "trend": trend,
        "confidence": int(confidence),
        "strength": strength,
        "support": float(close.tail(20).min()),
        "resistance": float(close.tail(20).max()),
    }

def format_analysis(a):
    now = datetime.now(UTC5).strftime("%H:%M:%S")
    return (
        "📈 <b>MARKET ANALYSIS</b>\n\n"
        f"💱 <b>Pair:</b> {a['pair']}\n"
        f"⏱ <b>Time:</b> {a['timeframe']}\n"
        f"🕒 <b>UTC+5:</b> {now}\n\n"
        f"💰 <b>Price:</b> {a['price']:.5f}\n\n"
        f"📊 <b>EMA 20:</b> {a['ema20']:.5f}\n"
        f"📊 <b>EMA 50:</b> {a['ema50']:.5f}\n"
        f"📉 <b>RSI 14:</b> {a['rsi']:.2f}\n\n"
        f"🔥 <b>Trend:</b> {a['trend']}\n"
        f"💪 <b>Strength:</b> {a['strength']}\n"
        f"🎯 <b>Confidence:</b> {a['confidence']}%\n\n"
        f"🚦 <b>SIGNAL:</b> {a['signal']}\n\n"
        f"📉 <b>Support:</b> {a['support']:.5f}\n"
        f"📈 <b>Resistance:</b> {a['resistance']:.5f}\n\n"
        "⚠️ <i>Automated technical analysis only. Results are not guaranteed.</i>"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings(context)
    await update.message.reply_text(
        "🤖 <b>TradeSignal AI</b>\n\nSelect an option below.",
        reply_markup=MAIN_MENU,
        parse_mode="HTML",
    )

async def show_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💱 <b>Select Pair:</b>", reply_markup=PAIR_MENU, parse_mode="HTML")

async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏱ <b>Select Time:</b>", reply_markup=TIME_MENU, parse_mode="HTML")

async def send_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = settings(context)
    await update.message.reply_text("🔄 Analyzing market data...")
    try:
        result = await asyncio.to_thread(analyze, s["pair"], s["timeframe"])
        s["history"].append({
            "time": datetime.now(UTC5).strftime("%Y-%m-%d %H:%M:%S"),
            "pair": result["pair"],
            "timeframe": result["timeframe"],
            "signal": result["signal"],
            "confidence": result["confidence"],
        })
        s["history"] = s["history"][-20:]
        await update.message.reply_text(format_analysis(result), parse_mode="HTML")
    except Exception as error:
        logger.exception("Analysis error")
        await update.message.reply_text(
            "⚠️ Market analysis could not be completed right now.\n\n"
            f"Reason: {error}"
        )

async def strongest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Scanning pairs...")
    best = None
    for pair in PAIRS:
        try:
            result = await asyncio.to_thread(analyze, pair, "5 MIN")
            if result["signal"] != "🟡 WAIT":
                if best is None or result["confidence"] > best["confidence"]:
                    best = result
        except Exception as error:
            logger.warning("Skipping %s: %s", pair, error)

    if best is None:
        await update.message.reply_text("🟡 No strong setup found right now.")
    else:
        await update.message.reply_text(
            "🔥 <b>STRONGEST CURRENT SETUP</b>\n\n" + format_analysis(best),
            parse_mode="HTML",
        )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = settings(context)["history"]
    if not items:
        await update.message.reply_text("📜 No analysis history yet.")
        return

    text = "📜 <b>SIGNAL HISTORY</b>\n\n"
    for item in reversed(items[-10:]):
        text += (
            f"🕒 {item['time']}\n"
            f"💱 {item['pair']} | ⏱ {item['timeframe']}\n"
            f"🚦 {item['signal']} | 🎯 {item['confidence']}%\n\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = settings(context)
    await update.message.reply_text(
        "⚙️ <b>SETTINGS</b>\n\n"
        f"💱 Pair: <b>{s['pair']}</b>\n"
        f"⏱ Time: <b>{s['timeframe']}</b>\n"
        "🕒 Timezone: <b>UTC+5</b>",
        parse_mode="HTML",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ <b>HOW TO USE</b>\n\n"
        "1️⃣ Select Pair\n"
        "2️⃣ Select Time\n"
        "3️⃣ Press Live Signals\n"
        "4️⃣ Read the analysis\n\n"
        "⚠️ Signals are not guaranteed results.",
        parse_mode="HTML",
    )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📈 Live Signals" or text == "📊 Market Analysis":
        await send_analysis(update, context)
    elif text == "🔥 Strongest Signal":
        await strongest(update, context)
    elif text == "💱 Select Pair":
        await show_pair(update, context)
    elif text == "⏱ Select Time":
        await show_time(update, context)
    elif text == "📜 Signal History":
        await history(update, context)
    elif text == "⚙️ Settings":
        await show_settings(update, context)
    elif text == "❓ Help":
        await help_command(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    s = settings(context)
    data = query.data

    if data.startswith("pair:"):
        pair = data.split(":", 1)[1]
        if pair in PAIRS:
            s["pair"] = pair
            await query.edit_message_text(
                f"✅ Selected pair: <b>{pair}</b>",
                parse_mode="HTML",
            )

    elif data.startswith("time:"):
        timeframe = data.split(":", 1)[1]
        if timeframe in TIMEFRAMES:
            s["timeframe"] = timeframe
            await query.edit_message_text(
                f"✅ Selected time: <b>{timeframe}</b>",
                parse_mode="HTML",
            )

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("TradeSignal AI is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
