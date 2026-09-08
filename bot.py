import os
import io
import logging
import asyncio
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


# =========================================================
# TRADE SIGNAL AI - ULTIMATE EDITION
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
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
    "EUR/CHF": "EURCHF=X",
    "EUR/AUD": "EURAUD=X",
    "EUR/CAD": "EURCAD=X",
    "EUR/NZD": "EURNZD=X",

    "GBP/JPY": "GBPJPY=X",
    "GBP/CHF": "GBPCHF=X",
    "GBP/AUD": "GBPAUD=X",
    "GBP/CAD": "GBPCAD=X",
    "GBP/NZD": "GBPNZD=X",

    "AUD/JPY": "AUDJPY=X",
    "AUD/CAD": "AUDCAD=X",
    "AUD/CHF": "AUDCHF=X",
    "AUD/NZD": "AUDNZD=X",

    "NZD/JPY": "NZDJPY=X",
    "NZD/CAD": "NZDCAD=X",
    "NZD/CHF": "NZDCHF=X",

    "CAD/JPY": "CADJPY=X",
    "CAD/CHF": "CADCHF=X",

    "CHF/JPY": "CHFJPY=X",
}


# =========================================================
# TIMEFRAMES
# =========================================================

TIMEFRAMES = {
    "1 MIN": "1m",
    "5 MIN": "5m",
}


# =========================================================
# MAIN MENU
# =========================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "🔥 Strongest Signal"],
        ["💱 Select Pair", "🌍 All Pairs"],
        ["⏱ Select Time", "📊 Market Analysis"],
        ["📜 Signal History", "⚙️ Settings"],
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
        [
            InlineKeyboardButton("🇦🇺 AUD/JPY", callback_data="pair:AUD/JPY"),
            InlineKeyboardButton("🇬🇧 GBP/CHF", callback_data="pair:GBP/CHF"),
        ],
    ]
)


# =========================================================
# TIME MENU
# =========================================================

TIME_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("⚡ 15 SEC", callback_data="time:15 SEC"),
            InlineKeyboardButton("⚡ 30 SEC", callback_data="time:30 SEC"),
        ],
        [
            InlineKeyboardButton("⏱ 1 MIN", callback_data="time:1 MIN"),
            InlineKeyboardButton("⏱ 5 MIN", callback_data="time:5 MIN"),
        ],
    ]
)


# =========================================================
# SETTINGS
# =========================================================

def settings(context):

    context.user_data.setdefault("pair", "EUR/USD")
    context.user_data.setdefault("timeframe", "1 MIN")
    context.user_data.setdefault("history", [])

    return context.user_data


# =========================================================
# FETCH MARKET DATA
# =========================================================

def fetch_data(pair, timeframe):

    if timeframe not in TIMEFRAMES:
        raise ValueError(
            "15 SEC and 30 SEC require a real-time tick/candle data provider. "
            "This bot will not fake second-level market data."
        )

    symbol = PAIRS[pair]
    interval = TIMEFRAMES[timeframe]

    periods = {
        "1m": "1d",
        "5m": "5d",
    }

    df = yf.download(
        symbol,
        period=periods[interval],
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False,
    )

    if df is None or df.empty:
        raise ValueError("Market data is unavailable.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]

    for column in required:
        if column not in df.columns:
            raise ValueError(f"Missing market column: {column}")

    df = df[required].copy()

    for column in required:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna()

    if len(df) < 60:
        raise ValueError("Not enough candles for analysis.")

    return df


# =========================================================
# RSI
# =========================================================

def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    )

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


# =========================================================
# MACD
# =========================================================

def calculate_macd(close):

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26

    signal = macd.ewm(span=9, adjust=False).mean()

    histogram = macd - signal

    return macd, signal, histogram


# =========================================================
# BOLLINGER BANDS
# =========================================================

def calculate_bollinger(close):

    middle = close.rolling(20).mean()

    std = close.rolling(20).std()

    upper = middle + (std * 2)
    lower = middle - (std * 2)

    return upper, middle, lower


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=14):

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1
    ).max(axis=1)

    atr = tr.rolling(period).mean()

    return atr


# =========================================================
# CANDLE PATTERN
# =========================================================

def candle_pattern(df):

    if len(df) < 3:
        return "NEUTRAL"

    last = df.iloc[-1]
    previous = df.iloc[-2]

    body = abs(last["Close"] - last["Open"])
    candle_range = max(
        last["High"] - last["Low"],
        1e-10
    )

    upper_wick = last["High"] - max(
        last["Open"],
        last["Close"]
    )

    lower_wick = min(
        last["Open"],
        last["Close"]
    ) - last["Low"]

    # Bullish engulfing
    if (
        previous["Close"] < previous["Open"]
        and last["Close"] > last["Open"]
        and last["Close"] > previous["Open"]
        and last["Open"] < previous["Close"]
    ):
        return "BULLISH ENGULFING"

    # Bearish engulfing
    if (
        previous["Close"] > previous["Open"]
        and last["Close"] < last["Open"]
        and last["Open"] > previous["Close"]
        and last["Close"] < previous["Open"]
    ):
        return "BEARISH ENGULFING"

    # Hammer
    if lower_wick > body * 2 and body / candle_range < 0.4:
        return "HAMMER"

    # Shooting star
    if upper_wick > body * 2 and body / candle_range < 0.4:
        return "SHOOTING STAR"

    if last["Close"] > last["Open"]:
        return "BULLISH CANDLE"

    if last["Close"] < last["Open"]:
        return "BEARISH CANDLE"

    return "NEUTRAL"


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def support_resistance(df):

    support = float(df["Low"].tail(30).min())

    resistance = float(df["High"].tail(30).max())

    return support, resistance


# =========================================================
# MAIN ANALYSIS
# =========================================================

def analyze(pair, timeframe):

    df = fetch_data(pair, timeframe)

    close = df["Close"]

    # EMA
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    # RSI
    rsi = calculate_rsi(close)

    # MACD
    macd, macd_signal, histogram = calculate_macd(close)

    # Bollinger
    bb_upper, bb_middle, bb_lower = calculate_bollinger(close)

    # ATR
    atr = calculate_atr(df)

    # Price
    price = float(close.iloc[-1])

    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])

    rsi_value = float(rsi.iloc[-1])

    macd_value = float(macd.iloc[-1])
    macd_signal_value = float(macd_signal.iloc[-1])

    upper_band = float(bb_upper.iloc[-1])
    lower_band = float(bb_lower.iloc[-1])

    atr_value = float(atr.iloc[-1])

    support, resistance = support_resistance(df)

    pattern = candle_pattern(df)

    buy_score = 0
    sell_score = 0

    reasons_buy = []
    reasons_sell = []


    # =====================================================
    # TREND
    # =====================================================

    if e20 > e50:

        buy_score += 25
        reasons_buy.append("EMA20 > EMA50")

    elif e20 < e50:

        sell_score += 25
        reasons_sell.append("EMA20 < EMA50")


    # =====================================================
    # PRICE POSITION
    # =====================================================

    if price > e20:

        buy_score += 15
        reasons_buy.append("Price above EMA20")

    else:

        sell_score += 15
        reasons_sell.append("Price below EMA20")


    # =====================================================
    # RSI
    # =====================================================

    if 52 <= rsi_value <= 68:

        buy_score += 15
        reasons_buy.append("RSI bullish zone")

    elif 32 <= rsi_value <= 48:

        sell_score += 15
        reasons_sell.append("RSI bearish zone")

    elif rsi_value < 30:

        buy_score += 8
        reasons_buy.append("RSI oversold")

    elif rsi_value > 70:

        sell_score += 8
        reasons_sell.append("RSI overbought")


    # =====================================================
    # MACD
    # =====================================================

    if macd_value > macd_signal_value:

        buy_score += 15
        reasons_buy.append("MACD bullish")

    else:

        sell_score += 15
        reasons_sell.append("MACD bearish")


    # =====================================================
    # MOMENTUM
    # =====================================================

    momentum = float(close.iloc[-1] - close.iloc[-5])

    if momentum > 0:

        buy_score += 10
        reasons_buy.append("Positive momentum")

    elif momentum < 0:

        sell_score += 10
        reasons_sell.append("Negative momentum")


    # =====================================================
    # CANDLE PATTERN
    # =====================================================

    bullish_patterns = [
        "BULLISH ENGULFING",
        "HAMMER",
        "BULLISH CANDLE",
    ]

    bearish_patterns = [
        "BEARISH ENGULFING",
        "SHOOTING STAR",
        "BEARISH CANDLE",
    ]

    if pattern in bullish_patterns:

        buy_score += 15
        reasons_buy.append(pattern)

    elif pattern in bearish_patterns:

        sell_score += 15
        reasons_sell.append(pattern)


    # =====================================================
    # BOLLINGER POSITION
    # =====================================================

    if price <= lower_band:

        buy_score += 8
        reasons_buy.append("Near lower Bollinger")

    elif price >= upper_band:

        sell_score += 8
        reasons_sell.append("Near upper Bollinger")


    # =====================================================
    # SIGNAL
    # =====================================================

    if buy_score >= 60 and buy_score > sell_score:

        signal = "🟢 BUY"
        trend = "📈 UP TREND"
        score = buy_score
        reasons = reasons_buy

    elif sell_score >= 60 and sell_score > buy_score:

        signal = "🔴 SELL"
        trend = "📉 DOWN TREND"
        score = sell_score
        reasons = reasons_sell

    else:

        signal = "🟡 WAIT"
        trend = "↔️ SIDEWAYS"
        score = max(buy_score, sell_score)
        reasons = ["No strong confirmation"]


    # =====================================================
    # ANALYSIS SCORE
    # =====================================================

    confidence = min(
        95,
        max(
            40,
            int(score)
        )
    )


    # =====================================================
    # STRENGTH
    # =====================================================

    trend_distance = (
        abs(e20 - e50)
        / max(abs(price), 1e-10)
    ) * 100000

    if trend_distance < 5:

        strength = "🟡 WEAK"

    elif trend_distance < 15:

        strength = "🟠 MEDIUM"

    else:

        strength = "🟢 STRONG"


    # =====================================================
    # MARKET SENTIMENT
    # =====================================================

    sentiment = min(
        100,
        max(
            0,
            int((buy_score / max(buy_score + sell_score, 1)) * 100)
        )
    )


    return {

        "pair": pair,
        "timeframe": timeframe,

        "price": price,

        "ema20": e20,
        "ema50": e50,

        "rsi": rsi_value,

        "macd": macd_value,
        "macd_signal": macd_signal_value,

        "bb_upper": upper_band,
        "bb_lower": lower_band,

        "atr": atr_value,

        "signal": signal,
        "trend": trend,

        "confidence": confidence,
        "strength": strength,

        "support": support,
        "resistance": resistance,

        "pattern": pattern,

        "sentiment": sentiment,

        "reasons": reasons,

        "df": df,
        "ema20_series": ema20,
        "ema50_series": ema50,
        "rsi_series": rsi,

    }


# =========================================================
# CREATE MARKET CHART
# =========================================================

def create_chart(result):

    df = result["df"].tail(60)

    ema20 = result["ema20_series"].tail(60)
    ema50 = result["ema50_series"].tail(60)

    rsi = result["rsi_series"].tail(60)

    fig = plt.figure(figsize=(12, 8))

    ax1 = plt.subplot2grid(
        (4, 1),
        (0, 0),
        rowspan=3
    )

    ax2 = plt.subplot2grid(
        (4, 1),
        (3, 0)
    )


    # Price line

    ax1.plot(
        df.index,
        df["Close"],
        label="Price"
    )

    ax1.plot(
        df.index,
        ema20,
        label="EMA 20"
    )

    ax1.plot(
        df.index,
        ema50,
        label="EMA 50"
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
        f"{result['pair']} | {result['timeframe']} | {result['signal']}"
    )

    ax1.legend()

    ax1.grid(True)


    # RSI

    ax2.plot(
        rsi.index,
        rsi,
        label="RSI 14"
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

    plt.savefig(
        buffer,
        format="png",
        dpi=150
    )

    buffer.seek(0)

    plt.close()

    return buffer


# =========================================================
# FORMAT ANALYSIS
# =========================================================

def format_analysis(a):

    now = datetime.now(UTC5).strftime("%H:%M:%S")

    reasons = "\n".join(
        f"✅ {reason}"
        for reason in a["reasons"][:5]
    )

    return (

        "👑 <b>TRADE SIGNAL AI - ULTIMATE VIP</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"💱 <b>PAIR:</b> {a['pair']}\n"
        f"⏱ <b>TIMEFRAME:</b> {a['timeframe']}\n"
        f"🕒 <b>UTC+5:</b> {now}\n\n"

        f"🚦 <b>SIGNAL:</b> {a['signal']}\n"
        f"🎯 <b>ANALYSIS SCORE:</b> {a['confidence']}%\n"
        f"🔥 <b>TREND:</b> {a['trend']}\n"
        f"💪 <b>STRENGTH:</b> {a['strength']}\n\n"

        "📊 <b>TECHNICAL ANALYSIS</b>\n\n"

        f"💰 Price: <b>{a['price']:.5f}</b>\n"
        f"📈 EMA 20: <b>{a['ema20']:.5f}</b>\n"
        f"📉 EMA 50: <b>{a['ema50']:.5f}</b>\n"
        f"📊 RSI 14: <b>{a['rsi']:.2f}</b>\n\n"

        f"📈 MACD: <b>{a['macd']:.6f}</b>\n"
        f"📊 MACD Signal: <b>{a['macd_signal']:.6f}</b>\n\n"

        f"📉 Support: <b>{a['support']:.5f}</b>\n"
        f"📈 Resistance: <b>{a['resistance']:.5f}</b>\n\n"

        f"🕯 <b>Candle:</b> {a['pattern']}\n"
        f"🌡 <b>ATR:</b> {a['atr']:.5f}\n"
        f"📊 <b>Market Sentiment:</b> {a['sentiment']}%\n\n"

        "🔍 <b>CONFIRMATIONS</b>\n"
        f"{reasons}\n\n"

        "⚠️ <i>This is automated technical analysis, "
        "not a guaranteed trading result.</i>"
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    settings(context)

    await update.message.reply_text(

        "👑 <b>TradeSignal AI</b>\n\n"
        "🚀 <b>ULTIMATE VIP EDITION</b>\n\n"

        "📊 EMA • RSI • MACD\n"
        "📈 Bollinger Bands\n"
        "🕯 Candle Analysis\n"
        "📉 Support & Resistance\n"
        "🔥 Trend Detection\n"
        "🖼 Market Chart\n\n"

        "🌍 Timezone: <b>UTC+5</b>\n\n"

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

        "💱 <b>Select Forex Pair:</b>",

        reply_markup=PAIR_MENU,

        parse_mode="HTML"

    )


# =========================================================
# ALL PAIRS
# =========================================================

async def all_pairs(
    update: Update,
    context: ContextTypes.D
