import os
import io
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("TradeSignalAI")

TOKEN = os.getenv("BOT_TOKEN")

# UTC+5
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
}


# =========================================================
# TIMEFRAMES
# =========================================================

TIMEFRAMES = {
    "1 MIN": "1m",
    "5 MIN": "5m",
}

PERIODS = {
    "1m": "1d",
    "5m": "5d",
}


# =========================================================
# MAIN MENU
# =========================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "🔥 Strongest Signal"],
        ["💱 Select Pair", "⏱ Select Time"],
        ["📊 Market Analysis", "📜 Signal History"],
        ["🌍 All Pairs", "⚙️ Settings"],
        ["👑 Ultimate VIP", "❓ Help"],
    ],
    resize_keyboard=True
)


# =========================================================
# PAIR MENU
# =========================================================

PAIR_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "EUR/USD",
                callback_data="pair:EUR/USD"
            ),
            InlineKeyboardButton(
                "GBP/USD",
                callback_data="pair:GBP/USD"
            ),
        ],
        [
            InlineKeyboardButton(
                "USD/JPY",
                callback_data="pair:USD/JPY"
            ),
            InlineKeyboardButton(
                "AUD/USD",
                callback_data="pair:AUD/USD"
            ),
        ],
        [
            InlineKeyboardButton(
                "USD/CAD",
                callback_data="pair:USD/CAD"
            ),
            InlineKeyboardButton(
                "USD/CHF",
                callback_data="pair:USD/CHF"
            ),
        ],
        [
            InlineKeyboardButton(
                "NZD/USD",
                callback_data="pair:NZD/USD"
            ),
            InlineKeyboardButton(
                "EUR/GBP",
                callback_data="pair:EUR/GBP"
            ),
        ],
        [
            InlineKeyboardButton(
                "EUR/JPY",
                callback_data="pair:EUR/JPY"
            ),
            InlineKeyboardButton(
                "GBP/JPY",
                callback_data="pair:GBP/JPY"
            ),
        ],
        [
            InlineKeyboardButton(
                "AUD/JPY",
                callback_data="pair:AUD/JPY"
            ),
            InlineKeyboardButton(
                "EUR/CHF",
                callback_data="pair:EUR/CHF"
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
            InlineKeyboardButton(
                "⚡ 15 SEC",
                callback_data="time:15 SEC"
            ),
            InlineKeyboardButton(
                "⚡ 30 SEC",
                callback_data="time:30 SEC"
            ),
        ],
        [
            InlineKeyboardButton(
                "⏱ 1 MIN",
                callback_data="time:1 MIN"
            ),
            InlineKeyboardButton(
                "⏱ 5 MIN",
                callback_data="time:5 MIN"
            ),
        ],
    ]
)


# =========================================================
# USER STATE
# =========================================================

def state(context):

    context.user_data.setdefault(
        "pair",
        "EUR/USD"
    )

    context.user_data.setdefault(
        "timeframe",
        "1 MIN"
    )

    context.user_data.setdefault(
        "history",
        []
    )

    return context.user_data


# =========================================================
# FETCH DATA
# =========================================================

def fetch_data(pair, timeframe):

    if pair not in PAIRS:
        raise ValueError("Unsupported pair")

    if timeframe not in TIMEFRAMES:
        raise ValueError(
            "15 SEC and 30 SEC need a dedicated "
            "real-time data provider."
        )

    interval = TIMEFRAMES[timeframe]

    df = yf.download(
        PAIRS[pair],
        period=PERIODS[interval],
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False
    )

    if df is None or df.empty:
        raise ValueError(
            "Market data is unavailable. Try again later."
        )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    needed = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    if any(column not in df.columns for column in needed):
        raise ValueError(
            "Market data format is incomplete."
        )

    df = df[needed].apply(
        pd.to_numeric,
        errors="coerce"
    ).dropna()

    if len(df) < 60:
        raise ValueError(
            "Not enough candles for analysis."
        )

    return df


# =========================================================
# RSI
# =========================================================

def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    result = 100 - 100 / (1 + rs)

    return result.fillna(50)


# =========================================================
# CANDLE PATTERN
# =========================================================

def candle_pattern(df):

    previous = df.iloc[-2]
    current = df.iloc[-1]

    if (
        previous.Close < previous.Open
        and current.Close > current.Open
        and current.Close >= previous.Open
        and current.Open <= previous.Close
    ):
        return "Bullish Engulfing", "BUY"

    if (
        previous.Close > previous.Open
        and current.Close < current.Open
        and current.Open >= previous.Close
        and current.Close <= previous.Open
    ):
        return "Bearish Engulfing", "SELL"

    if current.Close > current.Open:
        return "Bullish Candle", "BUY"

    if current.Close < current.Open:
        return "Bearish Candle", "SELL"

    return "Neutral", "WAIT"


# =========================================================
# ANALYSIS
# =========================================================

def analyze(pair, timeframe):

    df = fetch_data(pair, timeframe)

    close = df["Close"]

    # EMA
    ema20 = close.ewm(
        span=20,
        adjust=False
    ).mean()

    ema50 = close.ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI
    rsi14 = calculate_rsi(close)

    # MACD
    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26

    macd_signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    # Bollinger
    bb_middle = close.rolling(20).mean()

    bb_std = close.rolling(20).std()

    bb_upper = bb_middle + 2 * bb_std
    bb_lower = bb_middle - 2 * bb_std

    price = float(close.iloc[-1])

    buy = 0
    sell = 0

    # EMA trend

    if ema20.iloc[-1] > ema50.iloc[-1]:

        buy += 25

    else:

        sell += 25

    # Price position

    if price > ema20.iloc[-1]:

        buy += 15

    else:

        sell += 15

    # RSI

    rsi_value = float(rsi14.iloc[-1])

    if 52 <= rsi_value <= 70:

        buy += 15

    elif 30 <= rsi_value < 48:

        sell += 15

    elif rsi_value < 30:

        buy += 8

    elif rsi_value > 70:

        sell += 8

    # MACD

    if macd.iloc[-1] > macd_signal.iloc[-1]:

        buy += 15

    else:

        sell += 15

    # Momentum

    momentum = float(
        close.iloc[-1] -
        close.iloc[-5]
    )

    if momentum > 0:

        buy += 10

    elif momentum < 0:

        sell += 10

    # Candle

    pattern, direction = candle_pattern(df)

    if direction == "BUY":

        buy += 10

    elif direction == "SELL":

        sell += 10

    # Bollinger

    if (
        pd.notna(bb_lower.iloc[-1])
        and price <= bb_lower.iloc[-1]
    ):

        buy += 5

    if (
        pd.notna(bb_upper.iloc[-1])
        and price >= bb_upper.iloc[-1]
    ):

        sell += 5

    # Final signal

    if buy >= 55 and buy > sell:

        signal = "🟢 BUY"
        trend = "📈 UP TREND"
        score = buy

    elif sell >= 55 and sell > buy:

        signal = "🔴 SELL"
        trend = "📉 DOWN TREND"
        score = sell

    else:

        signal = "🟡 WAIT"
        trend = "↔️ SIDEWAYS"
        score = max(buy, sell)

    # Analysis score, not guaranteed win rate

    confidence = min(
        90,
        max(40, int(score))
    )

    support = float(
        df["Low"].tail(30).min()
    )

    resistance = float(
        df["High"].tail(30).max()
    )

    return {
        "pair": pair,
        "timeframe": timeframe,
        "signal": signal,
        "trend": trend,
        "confidence": confidence,
        "price": price,
        "ema20": float(ema20.iloc[-1]),
        "ema50": float(ema50.iloc[-1]),
        "rsi": rsi_value,
        "macd": float(macd.iloc[-1]),
        "macd_signal": float(
            macd_signal.iloc[-1]
        ),
        "support": support,
        "resistance": resistance,
        "pattern": pattern,
        "df": df,
        "ema20_series": ema20,
        "ema50_series": ema50,
        "rsi_series": rsi14,
    }


# =========================================================
# CREATE CHART
# =========================================================

def create_chart(result):

    df = result["df"].tail(60)

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(10, 7),
        height_ratios=[3, 1]
    )

    ax1.plot(
        df.index,
        df["Close"],
        label="Price"
    )

    ax1.plot(
        df.index,
        result["ema20_series"].tail(60),
        label="EMA20"
    )

    ax1.plot(
        df.index,
        result["ema50_series"].tail(60),
        label="EMA50"
    )

    ax1.axhline(
        result["support"],
        linestyle="--",
        label="Support"
    )

    ax1.axhline(
        result["resistance"],
        linestyle="--",
        label="Resistance"
    )

    ax1.set_title(
        f"{result['pair']} | "
        f"{result['timeframe']} | "
        f"{result['signal']}"
    )

    ax1.grid(True)
    ax1.legend()

    ax2.plot(
        df.index,
        result["rsi_series"].tail(60)
    )

    ax2.axhline(
        70,
        linestyle="--"
    )

    ax2.axhline(
        30,
        linestyle="--"
    )

    ax2.set_ylim(0, 100)
    ax2.set_title("RSI 14")
    ax2.grid(True)

    plt.tight_layout()

    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=130
    )

    buffer.seek(0)

    plt.close(fig)

    return buffer


# =========================================================
# FORMAT RESULT
# =========================================================

def format_analysis(result):

    now = datetime.now(UTC5).strftime(
        "%H:%M:%S"
    )

    return (
        "👑 <b>TRADE SIGNAL AI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"💱 Pair: <b>{result['pair']}</b>\n"
        f"⏱ Timeframe: <b>{result['timeframe']}</b>\n"
        f"🕒 UTC+5: <b>{now}</b>\n\n"

        f"🚦 Signal: <b>{result['signal']}</b>\n"
        f"🎯 Analysis Score: "
        f"<b>{result['confidence']}%</b>\n"
        f"🔥 Trend: <b>{result['trend']}</b>\n\n"

        "📊 <b>ANALYSIS</b>\n\n"

        f"💰 Price: "
        f"<b>{result['price']:.5f}</b>\n"

        f"📈 EMA20: "
        f"{result['ema20']:.5f}\n"

        f"📉 EMA50: "
        f"{result['ema50']:.5f}\n"

        f"📊 RSI14: "
        f"{result['rsi']:.2f}\n"

        f"📈 MACD: "
        f"{result['macd']:.6f}\n"

        f"🕯 Candle: "
        f"<b>{result['pattern']}</b>\n"

        f"🟩 Support: "
        f"{result['support']:.5f}\n"

        f"🟥 Resistance: "
        f"{result['resistance']:.5f}\n\n"

        "⚠️ <i>Technical analysis only. "
        "Profit is not guaranteed.</i>"
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    state(context)

    await update.message.reply_text(
        "👑 <b>TradeSignal AI - Ultimate</b>\n\n"
        "🌍 Timezone: UTC+5\n\n"
        "Select an option below 👇",
        reply_markup=MAIN_MENU,
        parse_mode="HTML"
    )


# =========================================================
# SHOW PAIRS
# =========================================================

async def show_pair(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "💱 <b>Select Pair:</b>",
        reply_markup=PAIR_MENU,
        parse_mode="HTML"
    )


# =========================================================
# SHOW TIME
# =========================================================

async def show_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "⏱ <b>Select Timeframe:</b>\n\n"
        "⚠️ 15 SEC and 30 SEC need a dedicated "
        "real-time data provider.",
        reply_markup=TIME_MENU,
        parse_mode="HTML"
    )


# =========================================================
# SEND ANALYSIS
# =========================================================

async def send_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = state(context)

    await update.message.reply_text(
        "🔄 <b>Analyzing market data...</b>",
        parse_mode="HTML"
    )

    try:

        result = await asyncio.to_thread(
            analyze,
            user["pair"],
            user["timeframe"]
        )

        chart = await asyncio.to_thread(
            create_chart,
            result
        )

        user["history"].append(
            (
                datetime.now(UTC5).strftime("%H:%M"),
                result["pair"],
                result["timeframe"],
                result["signal"],
                result["confidence"]
            )
        )

        user["history"] = user["history"][-20:]

        await update.message.reply_photo(
            chart,
            caption=format_analysis(result),
            parse_mode="HTML"
        )

    except Exception as error:

        logger.exception("Analysis failed")

        await update.message.reply_text(
            "⚠️ <b>Analysis could not be completed.</b>\n\n"
            f"<code>{error}</code>",
            parse_mode="HTML"
        )


# =========================================================
# STRONGEST SIGNAL
# =========================================================

async def strongest(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔥 <b>Scanning pairs...</b>",
        parse_mode="HTML"
    )

    best = None

    for pair in PAIRS:

        try:

            result = await asyncio.to_thread(
                analyze,
                pair,
                "5 MIN"
            )

            if (
                result["signal"] != "🟡 WAIT"
                and (
                    best is None
                    or result["confidence"]
                    > best["confidence"]
                )
            ):

                best = result

        except Exception as error:

            logger.warning(
                "%s skipped: %s",
                pair,
                error
            )

    if best is None:

        await update.message.reply_text(
            "🟡 No strong setup found right now."
        )

        return

    chart = await asyncio.to_thread(
        create_chart,
        best
    )

    await update.message.reply_photo(
        chart,
        caption=(
            "🔥 <b>STRONGEST CURRENT SETUP</b>\n\n"
            + format_analysis(best)
        ),
        parse_mode="HTML"
    )


# =========================================================
# HISTORY
# =========================================================

async def show_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    items = state(context)["history"]

    if not items:

        await update.message.reply_text(
            "📜 No analysis history yet."
        )

        return

    text = "📜 <b>SIGNAL HISTORY</b>\n\n"

    for time_value, pair, timeframe, signal, score in reversed(
        items[-10:]
    ):

        text += (
            f"🕒 {time_value} | "
            f"💱 {pair} | "
            f"⏱ {timeframe}\n"
            f"{signal} | 🎯 {score}%\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ALL PAIRS
# =========================================================

async def all_pairs(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "🌍 <b>SUPPORTED PAIRS</b>\n\n"
        + "\n".join(
            f"• {pair}"
            for pair in PAIRS
        )
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# SETTINGS
# =========================================================

async def show_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = state(context)

    await update.message.reply_text(
        "⚙️ <b>SETTINGS</b>\n\n"
        f"💱 Pair: <b>{user['pair']}</b>\n"
        f"⏱ Time: <b>{user['timeframe']}</b>\n"
        "🕒 Timezone: <b>UTC+5</b>",
        parse_mode="HTML"
    )


# =========================================================
# VIP
# =========================================================

async def vip(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "👑 <b>ULTIMATE FEATURES</b>\n\n"
        "✅ EMA20 / EMA50\n"
        "✅ RSI14\n"
        "✅ MACD\n"
        "✅ Bollinger Bands\n"
        "✅ Candle Analysis\n"
        "✅ Support / Resistance\n"
        "✅ Market Chart\n"
        "✅ Signal History\n"
        "✅ UTC+5",
        parse_mode="HTML"
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "❓ <b>HOW TO USE</b>\n\n"
        "1️⃣ Select Pair\n"
        "2️⃣ Select Time\n"
        "3️⃣ Press
