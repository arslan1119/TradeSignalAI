import os
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
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
    "AUD/JPY": "AUDJPY=X",
    "EUR/CHF": "EURCHF=X",
    "GBP/CHF": "GBPCHF=X",
    "AUD/CAD": "AUDCAD=X",
    "AUD/NZD": "AUDNZD=X",
    "CAD/JPY": "CADJPY=X",
    "CHF/JPY": "CHFJPY=X",
    "NZD/JPY": "NZDJPY=X",
}

TIMEFRAMES = {
    "5 SEC": "fast",
    "10 SEC": "fast",
    "15 SEC": "fast",
    "30 SEC": "fast",
    "1 MIN": "1m",
    "5 MIN": "5m",
    "10 MIN": "5m",
    "15 MIN": "15m",
    "30 MIN": "30m",
    "1 HOUR": "60m",
}

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "🔥 Strongest Signal"],
        ["💱 Select Pair", "⏱ Select Time"],
        ["📊 Market Analysis", "📜 Signal History"],
        ["⚙️ Settings", "❓ Help"],
    ],
    resize_keyboard=True
)

PAIR_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🇪🇺 EUR/USD", callback_data="pair:EUR/USD"),
            InlineKeyboardButton("🇬🇧 GBP/USD", callback_data="pair:GBP/USD"),
        ],
        [
            InlineKeyboardButton("🇺🇸 USD/JPY", callback_data="pair:USD/JPY"),
            InlineKeyboardButton("🇦🇺 AUD/USD", callback_data="pair:AUD/USD"),
        ],
        [
            InlineKeyboardButton("🇺🇸 USD/CAD", callback_data="pair:USD/CAD"),
            InlineKeyboardButton("🇺🇸 USD/CHF", callback_data="pair:USD/CHF"),
        ],
        [
            InlineKeyboardButton("🇳🇿 NZD/USD", callback_data="pair:NZD/USD"),
            InlineKeyboardButton("🇪🇺 EUR/GBP", callback_data="pair:EUR/GBP"),
        ],
        [
            InlineKeyboardButton("🇪🇺 EUR/JPY", callback_data="pair:EUR/JPY"),
            InlineKeyboardButton("🇬🇧 GBP/JPY", callback_data="pair:GBP/JPY"),
        ],
        [
            InlineKeyboardButton("🇦🇺 AUD/JPY", callback_data="pair:AUD/JPY"),
            InlineKeyboardButton("🇪🇺 EUR/CHF", callback_data="pair:EUR/CHF"),
        ],
        [
            InlineKeyboardButton("🇬🇧 GBP/CHF", callback_data="pair:GBP/CHF"),
            InlineKeyboardButton("🇦🇺 AUD/CAD", callback_data="pair:AUD/CAD"),
        ],
        [
            InlineKeyboardButton("🇦🇺 AUD/NZD", callback_data="pair:AUD/NZD"),
            InlineKeyboardButton("🇨🇦 CAD/JPY", callback_data="pair:CAD/JPY"),
        ],
        [
            InlineKeyboardButton("🇨🇭 CHF/JPY", callback_data="pair:CHF/JPY"),
            InlineKeyboardButton("🇳🇿 NZD/JPY", callback_data="pair:NZD/JPY"),
        ],
    ]
)

TIME_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("5 SEC", callback_data="time:5 SEC"),
            InlineKeyboardButton("10 SEC", callback_data="time:10 SEC"),
            InlineKeyboardButton("15 SEC", callback_data="time:15 SEC"),
        ],
        [
            InlineKeyboardButton("30 SEC", callback_data="time:30 SEC"),
            InlineKeyboardButton("1 MIN", callback_data="time:1 MIN"),
            InlineKeyboardButton("5 MIN", callback_data="time:5 MIN"),
        ],
        [
            InlineKeyboardButton("10 MIN", callback_data="time:10 MIN"),
            InlineKeyboardButton("15 MIN", callback_data="time:15 MIN"),
            InlineKeyboardButton("30 MIN", callback_data="time:30 MIN"),
        ],
        [InlineKeyboardButton("1 HOUR", callback_data="time:1 HOUR")],
    ]
)

def get_settings(context):
    data = context.user_data
    data.setdefault("pair", "EUR/USD")
    data.setdefault("timeframe", "5 MIN")
    data.setdefault("history", [])
    return data

def download_data(symbol, interval):
    if interval == "fast":
        interval = "1m"

    period_map = {
        "1m": "1d",
        "2m": "1d",
        "5m": "5d",
        "15m": "5d",
        "30m": "5d",
        "60m": "1mo",
    }
    period = period_map.get(interval, "5d")

    data = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False
    )

    if data is None or data.empty:
        raise ValueError("Market data is unavailable.")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data.dropna()

def calculate_analysis(pair_name, timeframe):
    symbol = PAIRS[pair_name]
    interval = TIMEFRAMES[timeframe]
    data = download_data(symbol, interval)

    if len(data) < 55:
        raise ValueError("Not enough candles for analysis.")

    close = pd.to_numeric(data["Close"], errors="coerce").dropna()

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    loss = loss.replace(0, 1e-10)
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    price = float(close.iloc[-1])
    ema20_value = float(ema20.iloc[-1])
    ema50_value = float(ema50.iloc[-1])
    rsi_value = float(rsi.iloc[-1])

    recent = close.tail(20)
    support = float(recent.min())
    resistance = float(recent.max())

    buy_score = 0
    sell_score = 0

    if ema20_value > ema50_value:
        buy_score += 35
    elif ema20_value < ema50_value:
        sell_score += 35

    if price > ema20_value:
        buy_score += 20
    elif price < ema20_value:
        sell_score += 20

    if 50 < rsi_value < 70:
        buy_score += 25
    elif 30 < rsi_value < 50:
        sell_score += 25
    elif rsi_value <= 30:
        buy_score += 15
    elif rsi_value >= 70:
        sell_score += 15

    momentum = float(close.iloc[-1] - close.iloc[-5])
    if momentum > 0:
        buy_score += 20
    elif momentum < 0:
        sell_score += 20

    if buy_score >= 60 and buy_score > sell_score:
        signal = "🟢 BUY"
        trend = "📈 UP TREND"
        confidence = min(95, buy_score)
    elif sell_score >= 60 and sell_score > buy_score:
        signal = "🔴 SELL"
        trend = "📉 DOWN TREND"
        confidence = min(95, sell_score)
    else:
        signal = "🟡 WAIT"
        trend = "↔️ SIDEWAYS"
        confidence = max(40, min(59, max(buy_score, sell_score)))

    strength_value = abs(ema20_value - ema50_value) / max(abs(price), 1e-10) * 100000
    if strength_value < 5:
        strength = "🟡 WEAK"
    elif strength_value < 15:
        strength = "🟠 MEDIUM"
    else:
        strength = "🟢 STRONG"

    return {
        "pair": pair_name,
        "timeframe": timeframe,
        "price": price,
        "ema20": ema20_value,
        "ema50": ema50_value,
        "rsi": rsi_value,
        "trend": trend,
        "strength": strength,
        "confidence": int(confidence),
        "signal": signal,
        "support": support,
        "resistance": resistance,
    }

def format_analysis(a):
    now = datetime.now(UTC5).strftime("%H:%M:%S")
    fast_note = ""
    if a["timeframe"] in {"5 SEC", "10 SEC", "15 SEC", "30 SEC"}:
        fast_note = "\n⚠️ Fast mode uses the latest available 1-minute market data as a proxy; it is not native tick/second data."

    return (
        "📈 <b>ULTIMATE MARKET ANALYSIS</b>\n\n"
        f"💱 <b>Pair:</b> {a['pair']}\n"
        f"⏱ <b>Selected time:</b> {a['timeframe']}\n"
        f"🕒 <b>UTC+5:</b> {now}\n\n"
        f"💰 <b>Price:</b> {a['price']:.5f}\n\n"
        f"📊 <b>EMA 20:</b> {a['ema20']:.5f}\n"
        f"📊 <b>EMA 50:</b> {a['ema50']:.5f}\n"
        f"📉 <b>RSI 14:</b> {a['rsi']:.2f}\n\n"
        f"🔥 <b>Trend:</b> {a['trend']}\n"
        f"💪 <b>Trend Strength:</b> {a['strength']}\n"
        f"🎯 <b>Signal Confidence:</b> {a['confidence']}%\n\n"
        f"🚦 <b>SIGNAL:</b> {a['signal']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📉 <b>Support:</b> {a['support']:.5f}\n"
        f"📈 <b>Resistance:</b> {a['resistance']:.5f}"
        f"{fast_note}\n\n"
        "⚠️ <i>This is automated technical analysis, not a guarantee of profit. Always manage risk.</i>"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_settings(context)
    await update.message.reply_text(
        "🤖 <b>TradeSignal AI — Ultimate Edition</b>\n\n"
        "UTC+5 • Multi-pair • EMA 20/50 • RSI 14 • Support/Resistance • Trend • Confidence\n\n"
        "Select an option below.",
        reply_markup=MAIN_MENU,
        parse_mode="HTML"
    )

async def show_pair_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💱 <b>Select a currency pair:</b>",
        reply_markup=PAIR_MENU,
        parse_mode="HTML"
    )

async def show_time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏱ <b>Select analysis/expiry mode:</b>",
        reply_markup=TIME_MENU,
        parse_mode="HTML"
    )

async def send_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_settings(context)
    try:
        await update.message.reply_text("🔄 Analyzing market data...")
        analysis = calculate_analysis(settings["pair"], settings["timeframe"])
        settings["history"].append({
            "time": datetime.now(UTC5).strftime("%Y-%m-%d %H:%M:%S"),
            "pair": analysis["pair"],
            "timeframe": analysis["timeframe"],
            "signal": analysis["signal"],
            "confidence": analysis["confidence"],
        })
        settings["history"] = settings["history"][-20:]
        await update.message.reply_text(
            format_analysis(analysis),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception("Analysis error")
        await update.message.reply_text(
            f"⚠️ Market analysis could not be completed right now.\n\nReason: {str(e)}"
        )

async def strongest_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Scanning major pairs...")
    best = None

    for pair in PAIRS:
        try:
            analysis = calculate_analysis(pair, "5 MIN")
            if analysis["signal"] == "🟡 WAIT":
                continue
            if best is None or analysis["confidence"] > best["confidence"]:
                best = analysis
        except Exception:
            continue

    if best is None:
        await update.message.reply_text(
            "🟡 No strong setup found right now. WAIT is safer than forcing a trade."
        )
        return

    await update.message.reply_text(
        "🔥 <b>STRONGEST CURRENT SETUP</b>\n\n" + format_analysis(best),
        parse_mode="HTML"
    )

async def market_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_analysis(update, context)

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_settings(context)
    items = settings["history"]

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

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_settings(context)
    text = (
        "⚙️ <b>SETTINGS</b>\n\n"
        f"💱 Pair: <b>{settings['pair']}</b>\n"
        f"⏱ Time: <b>{settings['timeframe']}</b>\n"
        "🕒 Timezone: <b>UTC+5</b>\n\n"
        "Use 💱 Select Pair and ⏱ Select Time to change settings."
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ <b>HOW TO USE</b>\n\n"
        "1️⃣ Select a pair\n"
        "2️⃣ Select a timeframe/expiry mode\n"
        "3️⃣ Press 📈 Live Signals or 📊 Market Analysis\n"
        "4️⃣ Read EMA, RSI, trend, support/resistance and confidence\n\n"
        "⚠️ BUY/SELL/WAIT are automated technical-analysis outputs, not guaranteed results.",
        parse_mode="HTML"
    )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📈 Live Signals":
        await send_analysis(update, context)
    elif text == "🔥 Strongest Signal":
        await strongest_signal(update, context)
    elif text == "💱 Select Pair":
        await show_pair_menu(update, context)
    elif text == "⏱ Select Time":
        await show_time_menu(update, context)
    elif text == "📊 Market Analysis":
        await market_analysis(update, context)
    elif text == "📜 Signal History":
        await history(update, context)
    elif text == "⚙️ Settings":
        await settings_menu(update, context)
    elif text == "❓ Help":
        await help_command(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = get_settings(context)
    data = query.data

    if data.startswith("pair:"):
        pair = data.split(":", 1)[1]
        if pair in PAIRS:
            settings["pair"] = pair
            await query.edit_message_text(
                f"✅ Selected pair: <b>{pair}</b>",
                parse_mode="HTML"
            )

    elif data.startswith("time:"):
        timeframe = data.split(":", 1)[1]
        if timeframe in TIMEFRAMES:
            settings["timeframe"] = timeframe
            await query.edit_message_text(
                f"✅ Selected time: <b>{timeframe}</b>\n🕒 Timezone: UTC+5",
                parse_mode="HTML"
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
