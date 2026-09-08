import os
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIGURATION
# =========================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("TradeSignalAI")

TOKEN = os.getenv("BOT_TOKEN")
UTC5 = timezone(timedelta(hours=5))

# =========================================================
# FOREX PAIRS
# =========================================================

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

# =========================================================
# TIMEFRAMES
# =========================================================

TIMEFRAMES = {
    "5 SEC": "1m",
    "10 SEC": "1m",
    "15 SEC": "1m",
    "30 SEC": "1m",
    "1 MIN": "1m",
    "5 MIN": "5m",
    "10 MIN": "5m",
    "15 MIN": "15m",
    "30 MIN": "30m",
    "1 HOUR": "1h",
}

# =========================================================
# MAIN MENU
# =========================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "🔥 Strongest Signal"],
        ["💱 Select Pair", "⏱ Select Time"],
        ["📊 Market Analysis", "📜 Signal History"],
        ["⚙️ Settings", "❓ Help"],
    ],
    resize_keyboard=True,
)

# =========================================================
# PAIR MENU
# =========================================================

PAIR_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "EUR/USD",
                callback_data="pair:EUR/USD",
            ),
            InlineKeyboardButton(
                "GBP/USD",
                callback_data="pair:GBP/USD",
            ),
        ],
        [
            InlineKeyboardButton(
                "USD/JPY",
                callback_data="pair:USD/JPY",
            ),
            InlineKeyboardButton(
                "AUD/USD",
                callback_data="pair:AUD/USD",
            ),
        ],
        [
            InlineKeyboardButton(
                "USD/CAD",
                callback_data="pair:USD/CAD",
            ),
            InlineKeyboardButton(
                "USD/CHF",
                callback_data="pair:USD/CHF",
            ),
        ],
        [
            InlineKeyboardButton(
                "NZD/USD",
                callback_data="pair:NZD/USD",
            ),
            InlineKeyboardButton(
                "EUR/GBP",
                callback_data="pair:EUR/GBP",
            ),
        ],
        [
            InlineKeyboardButton(
                "EUR/JPY",
                callback_data="pair:EUR/JPY",
            ),
            InlineKeyboardButton(
                "GBP/JPY",
                callback_data="pair:GBP/JPY",
            ),
        ],
        [
            InlineKeyboardButton(
                "AUD/JPY",
                callback_data="pair:AUD/JPY",
            ),
            InlineKeyboardButton(
                "EUR/CHF",
                callback_data="pair:EUR/CHF",
            ),
        ],
        [
            InlineKeyboardButton(
                "GBP/CHF",
                callback_data="pair:GBP/CHF",
            ),
            InlineKeyboardButton(
                "AUD/CAD",
                callback_data="pair:AUD/CAD",
            ),
        ],
        [
            InlineKeyboardButton(
                "AUD/NZD",
                callback_data="pair:AUD/NZD",
            ),
            InlineKeyboardButton(
                "CAD/JPY",
                callback_data="pair:CAD/JPY",
            ),
        ],
        [
            InlineKeyboardButton(
                "CHF/JPY",
                callback_data="pair:CHF/JPY",
            ),
            InlineKeyboardButton(
                "NZD/JPY",
                callback_data="pair:NZD/JPY",
            ),
        ],
    ]
)

# =========================================================
# TIME MENU
# =========================================================

TIME_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("5 SEC", callback_data="time:5 SEC"),
            InlineKeyboardButton("10 SEC", callback_data="time:10 SEC"),
        ],
        [
            InlineKeyboardButton("15 SEC", callback_data="time:15 SEC"),
            InlineKeyboardButton("30 SEC", callback_data="time:30 SEC"),
        ],
        [
            InlineKeyboardButton("1 MIN", callback_data="time:1 MIN"),
            InlineKeyboardButton("5 MIN", callback_data="time:5 MIN"),
        ],
        [
            InlineKeyboardButton("10 MIN", callback_data="time:10 MIN"),
            InlineKeyboardButton("15 MIN", callback_data="time:15 MIN"),
        ],
        [
            InlineKeyboardButton("30 MIN", callback_data="time:30 MIN"),
            InlineKeyboardButton("1 HOUR", callback_data="time:1 HOUR"),
        ],
    ]
)

# =========================================================
# USER SETTINGS
# =========================================================

def get_settings(context):
    context.user_data.setdefault("pair", "EUR/USD")
    context.user_data.setdefault("timeframe", "5 MIN")
    context.user_data.setdefault("history", [])

    return context.user_data


# =========================================================
# DOWNLOAD MARKET DATA
# =========================================================

def download_data(symbol, interval):

    period_map = {
        "1m": "5d",
        "5m": "5d",
        "15m": "5d",
        "30m": "1mo",
        "1h": "1mo",
    }

    period = period_map.get(interval, "5d")

    try:
        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception as error:
        raise ValueError(
            f"Could not download market data: {error}"
        )

    if data is None or data.empty:
        raise ValueError(
            "No market data is currently available."
        )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()

    if data.empty:
        raise ValueError(
            "Market data contains no usable candles."
        )

    return data


# =========================================================
# MARKET ANALYSIS
# =========================================================

def calculate_analysis(pair_name, timeframe):

    symbol = PAIRS[pair_name]
    interval = TIMEFRAMES[timeframe]

    data = download_data(symbol, interval)

    if "Close" not in data.columns:
        raise ValueError(
            "Close price data is unavailable."
        )

    close = pd.to_numeric(
        data["Close"],
        errors="coerce",
    ).dropna()

    if len(close) < 55:
        raise ValueError(
            "Not enough market candles for analysis."
        )

    # EMA 20
    ema20 = close.ewm(
        span=20,
        adjust=False,
    ).mean()

    # EMA 50
    ema50 = close.ewm(
        span=50,
        adjust=False,
    ).mean()

    # RSI 14
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.rolling(
        window=14
    ).mean()

    average_loss = loss.rolling(
        window=14
    ).mean()

    average_loss = average_loss.replace(
        0,
        0.0000000001,
    )

    rs = average_gain / average_loss

    rsi = 100 - (
        100 / (1 + rs)
    )

    # Latest values
    price = float(close.iloc[-1])

    ema20_value = float(
        ema20.iloc[-1]
    )

    ema50_value = float(
        ema50.iloc[-1]
    )

    rsi_value = float(
        rsi.iloc[-1]
    )

    # Support and resistance
    recent = close.tail(20)

    support = float(recent.min())
    resistance = float(recent.max())

    # =====================================================
    # SIGNAL SCORING
    # =====================================================

    buy_score = 0
    sell_score = 0

    # EMA trend
    if ema20_value > ema50_value:
        buy_score += 35

    elif ema20_value < ema50_value:
        sell_score += 35

    # Price position
    if price > ema20_value:
        buy_score += 20

    elif price < ema20_value:
        sell_score += 20

    # RSI
    if 50 < rsi_value < 70:
        buy_score += 25

    elif 30 < rsi_value < 50:
        sell_score += 25

    elif rsi_value <= 30:
        buy_score += 15

    elif rsi_value >= 70:
        sell_score += 15

    # Momentum
    if len(close) >= 5:

        momentum = float(
            close.iloc[-1] - close.iloc[-5]
        )

        if momentum > 0:
            buy_score += 20

        elif momentum < 0:
            sell_score += 20

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    if (
        buy_score >= 60
        and buy_score > sell_score
    ):

        signal = "🟢 BUY"
        trend = "📈 UP TREND"
        confidence = min(95, buy_score)

    elif (
        sell_score >= 60
        and sell_score > buy_score
    ):

        signal = "🔴 SELL"
        trend = "📉 DOWN TREND"
        confidence = min(95, sell_score)

    else:

        signal = "🟡 WAIT"
        trend = "↔️ SIDEWAYS"
        confidence = max(
            40,
            min(
                59,
                max(buy_score, sell_score),
            ),
        )

    # =====================================================
    # TREND STRENGTH
    # =====================================================

    strength_value = (
        abs(ema20_value - ema50_value)
        / max(abs(price), 0.00000001)
        * 100000
    )

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


# =========================================================
# FORMAT ANALYSIS
# =========================================================

def format_analysis(analysis):

    now = datetime.now(UTC5).strftime(
        "%H:%M:%S"
    )

    fast_note = ""

    if analysis["timeframe"] in {
        "5 SEC",
        "10 SEC",
        "15 SEC",
        "30 SEC",
    }:

        fast_note = (
            "\n\n⚠️ <b>Note:</b> Second-based modes use "
            "the latest available 1-minute data as an "
            "approximation."
        )

    text = (
        "📈 <b>TRADE SIGNAL AI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"💱 <b>Pair:</b> {analysis['pair']}\n"
        f"⏱ <b>Time:</b> {analysis['timeframe']}\n"
        f"🕒 <b>UTC+5:</b> {now}\n\n"

        f"💰 <b>Price:</b> {analysis['price']:.5f}\n\n"

        f"📊 <b>EMA 20:</b> {analysis['ema20']:.5f}\n"
        f"📊 <b>EMA 50:</b> {analysis['ema50']:.5f}\n"
        f"📉 <b>RSI 14:</b> {analysis['rsi']:.2f}\n\n"

        f"📈 <b>Trend:</b> {analysis['trend']}\n"
        f"💪 <b>Strength:</b> {analysis['strength']}\n"
        f"🎯 <b>Confidence:</b> {analysis['confidence']}%\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        f"🚦 <b>SIGNAL:</b> {analysis['signal']}\n\n"

        f"📉 <b>Support:</b> {analysis['support']:.5f}\n"
        f"📈 <b>Resistance:</b> {analysis['resistance']:.5f}"
        f"{fast_note}\n\n"

        "⚠️ <i>This is automated technical analysis. "
        "It does not guarantee profit.</i>"
    )

    return text


# =========================================================
# START COMMAND
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    get_settings(context)

    await update.message.reply_text(
        "🤖 <b>TradeSignal AI</b>\n\n"
        "📊 EMA 20/50\n"
        "📉 RSI 14\n"
        "📈 Trend Analysis\n"
        "📉 Support & Resistance\n"
        "🎯 Confidence Score\n"
        "🕒 UTC+5\n\n"
        "Choose an option below.",
        reply_markup=MAIN_MENU,
        parse_mode="HTML",
    )


# =========================================================
# PAIR MENU
# =========================================================

async def show_pair_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "💱 <b>Select a currency pair:</b>",
        reply_markup=PAIR_MENU,
        parse_mode="HTML",
    )


# =========================================================
# TIME MENU
# =========================================================

async def show_time_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "⏱ <b>Select timeframe:</b>",
        reply_markup=TIME_MENU,
        parse_mode="HTML",
    )


# =========================================================
# SEND ANALYSIS
# =========================================================

async def send_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    settings = get_settings(context)

    await update.message.reply_text(
        "🔄 Analyzing market data..."
    )

    try:

        analysis = calculate_analysis(
            settings["pair"],
            settings["timeframe"],
        )

        settings["history"].append(
            {
                "time": datetime.now(UTC5).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "pair": analysis["pair"],
                "timeframe": analysis["timeframe"],
                "signal": analysis["signal"],
                "confidence": analysis["confidence"],
            }
        )

        settings["history"] = (
            settings["history"][-20:]
        )

        await update.message.reply_text(
            format_analysis(analysis),
            parse_mode="HTML",
        )

    except Exception as error:

        logger.exception(
            "Analysis error"
        )

        await update.message.reply_text(
            "⚠️ <b>Market analysis could not be completed.</b>\n\n"
            f"Reason: <code>{str(error)}</code>",
            parse_mode="HTML",
        )


# =========================================================
# STRONGEST SIGNAL
# =========================================================

async def strongest_signal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🔥 Scanning currency pairs..."
    )

    best = None

    for pair in PAIRS:

        try:

            analysis = calculate_analysis(
                pair,
                "5 MIN",
            )

            if analysis["signal"] == "🟡 WAIT":
                continue

            if best is None:

                best = analysis

            elif (
                analysis["confidence"]
                > best["confidence"]
            ):

                best = analysis

        except Exception as error:

            logger.warning(
                "Could not analyze %s: %s",
                pair,
                error,
            )

    if best is None:

        await update.message.reply_text(
            "🟡 No strong setup was found right now.\n\n"
            "WAIT is safer than forcing a trade."
        )

        return

    await update.message.reply_text(
        "🔥 <b>STRONGEST CURRENT SETUP</b>\n\n"
        + format_analysis(best),
        parse_mode="HTML",
    )


# =========================================================
# HISTORY
# =========================================================

async def show_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    settings = get_settings(context)

    history = settings["history"]

    if not history:

        await update.message.reply_text(
            "📜 No signal history yet."
        )

        return

    text = (
        "📜 <b>SIGNAL HISTORY</b>\n\n"
    )

    for item in reversed(history[-10:]):

        text += (
            f"🕒 {item['time']}\n"
            f"💱 {item['pair']} | "
            f"⏱ {item['timeframe']}\n"
            f"🚦 {item['signal']} | "
            f"🎯 {item['confidence']}%\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================================================
# SETTINGS
# =========================================================

async def settings_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    settings = get_settings(context)

    text = (
        "⚙️ <b>SETTINGS</b>\n\n"
        f"💱 Pair: <b>{settings['pair']}</b>\n"
        f"⏱ Time: <b>{settings['timeframe']}</b>\n"
        "🕒 Timezone: <b>UTC+5</b>\n\n"
        "Use 💱 Select Pair and "
        "⏱ Select Time to change settings."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        "❓ <b>HOW TO USE</b>\n\n"

        "1️⃣ Select a currency pair\n"
        "2️⃣ Select a timeframe\n"
        "3️⃣ Press 📈 Live Signals\n"
        "4️⃣ Read the analysis\n\n"

        "📊 The bot analyzes:\n"
        "• EMA 20\n"
        "• EMA 50\n"
        "• RSI 14\n"
        "• Momentum\n"
        "• Support\n"
        "• Resistance\n"
        "• Trend strength\n\n"

        "⚠️ BUY/SELL/WAIT are automated "
        "technical-analysis outputs and "
        "are not guaranteed results."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text

    if text == "📈 Live Signals":

        await send_analysis(
            update,
            context,
        )

    elif text == "🔥 Strongest Signal":

        await strongest_signal(
            update,
            context,
        )

    elif text == "💱 Select Pair":

        await show_pair_menu(
            update,
            context,
        )

    elif text == "⏱ Select Time":

        await show_time_menu(
            update,
            context,
        )

    elif text == "📊 Market Analysis":

        await send_analysis(
            update,
            context,
        )

    elif text == "📜 Signal History":

        await show_history(
            update,
            context,
        )

    elif text == "⚙️ Settings":

        await settings_menu(
            update,
            context,
        )

    elif text == "❓ Help":

        await help_command(
            update,
            contex
