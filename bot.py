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


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("TradeSignalAI")


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")

UTC5 = timezone(timedelta(hours=5))


# ============================================================
# FOREX PAIRS
# ============================================================

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
    "EUR/CHF": "EURCHF=X",

    "GBP/JPY": "GBPJPY=X",
    "GBP/CHF": "GBPCHF=X",

    "AUD/JPY": "AUDJPY=X",
    "AUD/CAD": "AUDCAD=X",
    "AUD/NZD": "AUDNZD=X",

    "CAD/JPY": "CADJPY=X",

    "CHF/JPY": "CHFJPY=X",

    "NZD/JPY": "NZDJPY=X",
}


# ============================================================
# TIMEFRAMES
# ============================================================

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
    "1 HOUR": "60m",
}


# ============================================================
# MAIN MENU
# ============================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "🔥 Strongest Signal"],
        ["💱 Select Pair", "⏱ Select Time"],
        ["📊 Market Analysis", "📜 Signal History"],
        ["⚙️ Settings", "❓ Help"],
    ],
    resize_keyboard=True,
)


# ============================================================
# PAIR MENU
# ============================================================

PAIR_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "🇪🇺 EUR/USD",
                callback_data="pair:EUR/USD",
            ),
            InlineKeyboardButton(
                "🇬🇧 GBP/USD",
                callback_data="pair:GBP/USD",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇯🇵 USD/JPY",
                callback_data="pair:USD/JPY",
            ),
            InlineKeyboardButton(
                "🇦🇺 AUD/USD",
                callback_data="pair:AUD/USD",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇨🇦 USD/CAD",
                callback_data="pair:USD/CAD",
            ),
            InlineKeyboardButton(
                "🇨🇭 USD/CHF",
                callback_data="pair:USD/CHF",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇳🇿 NZD/USD",
                callback_data="pair:NZD/USD",
            ),
            InlineKeyboardButton(
                "🇪🇺 EUR/GBP",
                callback_data="pair:EUR/GBP",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇪🇺 EUR/JPY",
                callback_data="pair:EUR/JPY",
            ),
            InlineKeyboardButton(
                "🇪🇺 EUR/CHF",
                callback_data="pair:EUR/CHF",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇬🇧 GBP/JPY",
                callback_data="pair:GBP/JPY",
            ),
            InlineKeyboardButton(
                "🇬🇧 GBP/CHF",
                callback_data="pair:GBP/CHF",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇦🇺 AUD/JPY",
                callback_data="pair:AUD/JPY",
            ),
            InlineKeyboardButton(
                "🇦🇺 AUD/CAD",
                callback_data="pair:AUD/CAD",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇦🇺 AUD/NZD",
                callback_data="pair:AUD/NZD",
            ),
            InlineKeyboardButton(
                "🇨🇦 CAD/JPY",
                callback_data="pair:CAD/JPY",
            ),
        ],
        [
            InlineKeyboardButton(
                "🇨🇭 CHF/JPY",
                callback_data="pair:CHF/JPY",
            ),
            InlineKeyboardButton(
                "🇳🇿 NZD/JPY",
                callback_data="pair:NZD/JPY",
            ),
        ],
    ]
)


# ============================================================
# TIME MENU
# ============================================================

TIME_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "5 SEC",
                callback_data="time:5 SEC",
            ),
            InlineKeyboardButton(
                "10 SEC",
                callback_data="time:10 SEC",
            ),
            InlineKeyboardButton(
                "15 SEC",
                callback_data="time:15 SEC",
            ),
        ],
        [
            InlineKeyboardButton(
                "30 SEC",
                callback_data="time:30 SEC",
            ),
            InlineKeyboardButton(
                "1 MIN",
                callback_data="time:1 MIN",
            ),
            InlineKeyboardButton(
                "5 MIN",
                callback_data="time:5 MIN",
            ),
        ],
        [
            InlineKeyboardButton(
                "10 MIN",
                callback_data="time:10 MIN",
            ),
            InlineKeyboardButton(
                "15 MIN",
                callback_data="time:15 MIN",
            ),
            InlineKeyboardButton(
                "30 MIN",
                callback_data="time:30 MIN",
            ),
        ],
        [
            InlineKeyboardButton(
                "1 HOUR",
                callback_data="time:1 HOUR",
            ),
        ],
    ]
)


# ============================================================
# USER SETTINGS
# ============================================================

def get_settings(context):

    data = context.user_data

    if "pair" not in data:
        data["pair"] = "EUR/USD"

    if "timeframe" not in data:
        data["timeframe"] = "5 MIN"

    if "history" not in data:
        data["history"] = []

    return data


# ============================================================
# DOWNLOAD MARKET DATA
# ============================================================

def download_data(symbol, interval):

    period_map = {
        "1m": "1d",
        "2m": "5d",
        "5m": "5d",
        "15m": "5d",
        "30m": "5d",
        "60m": "1mo",
    }

    period = period_map.get(interval, "5d")

    data = None

    # --------------------------------------------------------
    # METHOD 1
    # --------------------------------------------------------

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

        logger.warning(
            "yf.download failed for %s: %s",
            symbol,
            error,
        )

    # --------------------------------------------------------
    # METHOD 2
    # --------------------------------------------------------

    if data is None or data.empty:

        try:

            ticker = yf.Ticker(symbol)

            data = ticker.history(
                period=period,
                interval=interval,
                auto_adjust=False,
            )

        except Exception as error:

            logger.warning(
                "Ticker.history failed for %s: %s",
                symbol,
                error,
            )

    # --------------------------------------------------------
    # CHECK DATA
    # --------------------------------------------------------

    if data is None or data.empty:

        raise ValueError(
            "Market data is temporarily unavailable. "
            "Please try again in a few seconds."
        )

    # --------------------------------------------------------
    # FIX MULTIINDEX
    # --------------------------------------------------------

    if isinstance(data.columns, pd.MultiIndex):

        data.columns = data.columns.get_level_values(0)

    # --------------------------------------------------------
    # CLEAN DATA
    # --------------------------------------------------------

    data = data.dropna(how="all")

    if "Close" not in data.columns:

        raise ValueError(
            "Market price data could not be found."
        )

    return data


# ============================================================
# CALCULATE ANALYSIS
# ============================================================

def calculate_analysis(pair_name, timeframe):

    if pair_name not in PAIRS:
        raise ValueError("Unknown currency pair.")

    if timeframe not in TIMEFRAMES:
        raise ValueError("Unknown timeframe.")

    symbol = PAIRS[pair_name]

    interval = TIMEFRAMES[timeframe]

    data = download_data(
        symbol,
        interval,
    )

    close = pd.to_numeric(
        data["Close"],
        errors="coerce",
    ).dropna()

    if len(close) < 55:

        raise ValueError(
            f"Not enough market candles. "
            f"Received only {len(close)} candles."
        )

    # ========================================================
    # EMA 20
    # ========================================================

    ema20 = close.ewm(
        span=20,
        adjust=False,
    ).mean()

    # ========================================================
    # EMA 50
    # ========================================================

    ema50 = close.ewm(
        span=50,
        adjust=False,
    ).mean()

    # ========================================================
    # RSI 14
    # ========================================================

    delta = close.diff()

    gain = delta.where(
        delta > 0,
        0.0,
    )

    loss = -delta.where(
        delta < 0,
        0.0,
    )

    avg_gain = gain.rolling(
        window=14,
        min_periods=14,
    ).mean()

    avg_loss = loss.rolling(
        window=14,
        min_periods=14,
    ).mean()

    avg_loss = avg_loss.replace(
        0,
        1e-10,
    )

    rs = avg_gain / avg_loss

    rsi = 100 - (
        100 / (1 + rs)
    )

    # ========================================================
    # LATEST VALUES
    # ========================================================

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

    if pd.isna(rsi_value):

        rsi_value = 50.0

    # ========================================================
    # SUPPORT / RESISTANCE
    # ========================================================

    recent = close.tail(30)

    support = float(
        recent.min()
    )

    resistance = float(
        recent.max()
    )

    # ========================================================
    # SIGNAL SCORING
    # ========================================================

    buy_score = 0

    sell_score = 0

    # --------------------------------------------------------
    # EMA TREND
    # --------------------------------------------------------

    if ema20_value > ema50_value:

        buy_score += 35

    elif ema20_value < ema50_value:

        sell_score += 35

    # --------------------------------------------------------
    # PRICE POSITION
    # --------------------------------------------------------

    if price > ema20_value:

        buy_score += 20

    elif price < ema20_value:

        sell_score += 20

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if 50 < rsi_value < 70:

        buy_score += 25

    elif 30 < rsi_value < 50:

        sell_score += 25

    elif rsi_value <= 30:

        buy_score += 15

    elif rsi_value >= 70:

        sell_score += 15

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if len(close) >= 5:

        momentum = float(
            close.iloc[-1]
            - close.iloc[-5]
        )

        if momentum > 0:

            buy_score += 20

        elif momentum < 0:

            sell_score += 20

    # ========================================================
    # FINAL SIGNAL
    # ========================================================

    if (
        buy_score >= 60
        and buy_score > sell_score
    ):

        signal = "🟢 BUY"

        trend = "📈 UP TREND"

        confidence = min(
            95,
            buy_score,
        )

    elif (
        sell_score >= 60
        and sell_score > buy_score
    ):

        signal = "🔴 SELL"

        trend = "📉 DOWN TREND"

        confidence = min(
            95,
            sell_score,
        )

    else:

        signal = "🟡 WAIT"

        trend = "↔️ SIDEWAYS"

        confidence = max(
            40,
            min(
                59,
                max(
                    buy_score,
                    sell_score,
                ),
            ),
        )

    # ========================================================
    # TREND STRENGTH
    # ========================================================

    strength_value = (
        abs(
            ema20_value
            - ema50_value
        )
        / max(
            abs(price),
            1e-10,
        )
        * 100000
    )

    if strength_value < 5:

        strength = "🟡 WEAK"

    elif strength_value < 15:

        strength = "🟠 MEDIUM"

    else:

        strength = "🟢 STRONG"

    # ========================================================
    # RETURN
    # ========================================================

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


# ============================================================
# FORMAT ANALYSIS
# ============================================================

def format_analysis(a):

    now = datetime.now(
        UTC5
    ).strftime("%H:%M:%S")

    fast_note = ""

    if a["timeframe"] in {
        "5 SEC",
        "10 SEC",
        "15 SEC",
        "30 SEC",
    }:

        fast_note = (
            "\n\n⚠️ <b>Fast Mode:</b> "
            "Yahoo Finance does not provide native "
            "5–30 second Forex candles. "
            "The latest available 1-minute data is used "
            "as an analysis proxy."
        )

    return (

        "📈 <b>ULTIMATE PROFESSIONAL MARKET ANALYSIS</b>\n\n"

        f"💱 <b>Pair:</b> {a['pair']}\n"

        f"⏱ <b>Selected Time:</b> "
        f"{a['timeframe']}\n"

        f"🕒 <b>UTC+5:</b> {now}\n\n"

        f"💰 <b>Price:</b> "
        f"{a['price']:.5f}\n\n"

        f"📊 <b>EMA 20:</b> "
        f"{a['ema20']:.5f}\n"

        f"📊 <b>EMA 50:</b> "
        f"{a['ema50']:.5f}\n"

        f"📉 <b>RSI 14:</b> "
        f"{a['rsi']:.2f}\n\n"

        f"🔥 <b>Trend:</b> "
        f"{a['trend']}\n"

        f"💪 <b>Trend Strength:</b> "
        f"{a['strength']}\n"

        f"🎯 <b>Signal Confidence:</b> "
        f"{a['confidence']}%\n\n"

        f"🚦 <b>SIGNAL:</b> "
        f"{a['signal']}\n\n"

        "━━━━━━━━━━━━━━━━━━\n\n"

        f"📉 <b>Support:</b> "
        f"{a['support']:.5f}\n"

        f"📈 <b>Resistance:</b> "
        f"{a['resistance']:.5f}"

        f"{fast_note}"

        "\n\n⚠️ <i>"
        "This is automated technical analysis "
        "for informational purposes and does not "
        "guarantee trading results."
        "</i>"

    )


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    get_settings(context)

    await update.message.reply_text(

        "🤖 <b>TradeSignal AI — Ultimate Edition</b>\n\n"

        "🌍 Multi-Pair Forex Analysis\n"
        "🕒 UTC+5 Timezone\n"
        "📊 EMA 20 / EMA 50\n"
        "📉 RSI 14\n"
        "📈 Trend Analysis\n"
        "📉 Support & Resistance\n"
        "💪 Trend Strength\n"
        "🎯 Signal Confidence\n"
        "⏱ Multiple Timeframes\n\n"

        "Select an option below.",

        reply_markup=MAIN_MENU,

        parse_mode="HTML",

    )


# ============================================================
# SHOW PAIRS
# ============================================================

async def show_pair_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(

        "💱 <b>Select a currency pair:</b>",

        reply_markup=PAIR_MENU,

        parse_mode="HTML",

    )


# ============================================================
# SHOW TIME
# ============================================================

async def show_time_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(

        "⏱ <b>Select analysis mode:</b>",

        reply_markup=TIME_MENU,

        parse_mode="HTML",

    )


# ============================================================
# SEND ANALYSIS
# ============================================================

async def send_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    settings = get_settings(context)

    try:

        await update.message.reply_text(
            "🔄 <b>Analyzing market data...</b>",
            parse_mode="HTML",
        )

        analysis = calculate_analysis(

            settings["pair"],

            settings["timeframe"],

        )

        settings["history"].append({

            "time": datetime.now(
                UTC5
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "pair": analysis["pair"],

            "timeframe": analysis["timeframe"],

            "signal": analysis["signal"],

            "confidence": analysis["confidence"],

        })

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

            "⚠️ <b>Market analysis is temporarily unavailable.</b>\n\n"

            f"<b>Reason:</b> {str(error)}\n\n"

            "Please try again in a few seconds.",

            parse_mode="HTML",

        )


# ============================================================
# STRONGEST SIGNAL
# ============================================================

async def strongest_signal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🔥 <b>Scanning major pairs...</b>",
        parse_mode="HTM
