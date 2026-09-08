import os
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")

UTC5 = timezone(timedelta(hours=5))

signal_history = []
user_settings = {}


# ============================================================
# FOREX PAIRS
# ============================================================

PAIRS = {
    "🇪🇺 EUR/USD": "EURUSD=X",
    "🇬🇧 GBP/USD": "GBPUSD=X",
    "🇺🇸 USD/JPY": "JPY=X",
    "🇦🇺 AUD/USD": "AUDUSD=X",
    "🇺🇸 USD/CAD": "CAD=X",
    "🇳🇿 NZD/USD": "NZDUSD=X",
    "🇪🇺 EUR/GBP": "EURGBP=X",
    "🇪🇺 EUR/JPY": "EURJPY=X",
    "🇬🇧 GBP/JPY": "GBPJPY=X",
    "🇦🇺 AUD/JPY": "AUDJPY=X",
    "🇨🇭 USD/CHF": "CHF=X",
    "🇪🇺 EUR/CHF": "EURCHF=X",
    "🇬🇧 GBP/CHF": "GBPCHF=X",
    "🇦🇺 AUD/CAD": "AUDCAD=X",
    "🇦🇺 AUD/NZD": "AUDNZD=X",
    "🇳🇿 NZD/JPY": "NZDJPY=X",
}


# ============================================================
# TIMEFRAMES
# ============================================================

TIMEFRAMES = {
    "⏱ 5 SEC": "1m",
    "⏱ 10 SEC": "1m",
    "⏱ 15 SEC": "1m",
    "⏱ 30 SEC": "1m",
    "🕐 1 MIN": "1m",
    "🕔 5 MIN": "5m",
    "🕙 10 MIN": "5m",
}


# ============================================================
# MAIN MENU
# ============================================================

MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "🔥 Strongest Signal"],
        ["💱 Select Pair", "⏱ Select Time"],
        ["📊 Market Analysis", "📜 Signal History"],
        ["⚙️ Settings", "❓ Help"],
    ],
    resize_keyboard=True
)


TIME_MENU = ReplyKeyboardMarkup(
    [
        ["⏱ 5 SEC", "⏱ 10 SEC"],
        ["⏱ 15 SEC", "⏱ 30 SEC"],
        ["🕐 1 MIN", "🕔 5 MIN"],
        ["🕙 10 MIN"],
        ["🔙 Back"],
    ],
    resize_keyboard=True
)


PAIR_MENU = ReplyKeyboardMarkup(
    [
        ["🇪🇺 EUR/USD", "🇬🇧 GBP/USD"],
        ["🇺🇸 USD/JPY", "🇦🇺 AUD/USD"],
        ["🇺🇸 USD/CAD", "🇳🇿 NZD/USD"],
        ["🇪🇺 EUR/GBP", "🇪🇺 EUR/JPY"],
        ["🇬🇧 GBP/JPY", "🇦🇺 AUD/JPY"],
        ["🇨🇭 USD/CHF", "🇪🇺 EUR/CHF"],
        ["🇬🇧 GBP/CHF", "🇦🇺 AUD/CAD"],
        ["🇦🇺 AUD/NZD", "🇳🇿 NZD/JPY"],
        ["🔙 Back"],
    ],
    resize_keyboard=True
)


# ============================================================
# USER SETTINGS
# ============================================================

def get_user_config(user_id):

    if user_id not in user_settings:

        user_settings[user_id] = {
            "time_button": "🕔 5 MIN",
            "timeframe": "5m",
            "pair_name": "🇪🇺 EUR/USD",
            "symbol": "EURUSD=X",
        }

    return user_settings[user_id]


# ============================================================
# MARKET ANALYSIS
# ============================================================

def analyze_market(symbol="EURUSD=X", timeframe="5m"):

    try:

        # Yahoo Finance does not provide true public
        # 5-second/10-second/15-second/30-second candles.
        # Short buttons therefore use the latest 1-minute data.

        period = "5d"

        if timeframe == "1m":
            period = "1d"

        data = yf.download(
            symbol,
            period=period,
            interval=timeframe,
            progress=False,
            auto_adjust=False,
        )

        if data.empty:

            return {
                "error": "Bazardan maglumat alyp bolmady."
            }

        # Handle MultiIndex columns safely

        close = data["Close"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        high = data["High"]

        if isinstance(high, pd.DataFrame):
            high = high.iloc[:, 0]

        low = data["Low"]

        if isinstance(low, pd.DataFrame):
            low = low.iloc[:, 0]

        close = close.dropna()

        if len(close) < 60:

            return {
                "error": "Analiz üçin maglumat ýeterlik däl."
            }


        # ====================================================
        # EMA
        # ====================================================

        ema20 = close.ewm(
            span=20,
            adjust=False
        ).mean()

        ema50 = close.ewm(
            span=50,
            adjust=False
        ).mean()


        # ====================================================
        # RSI 14
        # ====================================================

        delta = close.diff()

        gain = delta.clip(lower=0)

        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(
            window=14
        ).mean()

        avg_loss = loss.rolling(
            window=14
        ).mean()

        avg_loss = avg_loss.replace(0, 0.0000001)

        rs = avg_gain / avg_loss

        rsi = 100 - (
            100 / (1 + rs)
        )


        # ====================================================
        # LATEST VALUES
        # ====================================================

        price = float(close.iloc[-1])

        ema20_value = float(ema20.iloc[-1])

        ema50_value = float(ema50.iloc[-1])

        rsi_value = float(rsi.iloc[-1])


        # ====================================================
        # TREND
        # ====================================================

        if ema20_value > ema50_value:

            trend = "📈 UP TREND"

        elif ema20_value < ema50_value:

            trend = "📉 DOWN TREND"

        else:

            trend = "↔️ SIDEWAYS"


        # ====================================================
        # TREND STRENGTH
        # ====================================================

        ema_difference = abs(
            ema20_value - ema50_value
        )

        percentage_difference = (
            ema_difference / price
        ) * 100

        strength = min(
            100,
            percentage_difference * 10000
        )

        if strength < 20:

            strength_text = "🟡 WEAK"

        elif strength < 50:

            strength_text = "🟠 MEDIUM"

        else:

            strength_text = "🟢 STRONG"


        # ====================================================
        # VOLATILITY
        # ====================================================

        recent_returns = close.pct_change().tail(20)

        volatility = float(
            recent_returns.std() * 100
        )

        if volatility < 0.02:

            volatility_text = "🟢 LOW"

        elif volatility < 0.08:

            volatility_text = "🟠 MEDIUM"

        else:

            volatility_text = "🔴 HIGH"


        # ====================================================
        # SUPPORT / RESISTANCE
        # ====================================================

        recent_low = low.tail(30)

        recent_high = high.tail(30)

        support = float(recent_low.min())

        resistance = float(recent_high.max())


        # ====================================================
        # CANDLE MOMENTUM
        # ====================================================

        last_close = float(close.iloc[-1])

        previous_close = float(close.iloc[-2])

        momentum = (
            (last_close - previous_close)
            / previous_close
        ) * 100


        # ====================================================
        # BUY SCORE
        # ====================================================

        buy_score = 0

        if ema20_value > ema50_value:
            buy_score += 30

        if price > ema20_value:
            buy_score += 20

        if 50 < rsi_value < 70:
            buy_score += 25

        if momentum > 0:
            buy_score += 15

        if strength >= 30:
            buy_score += 10


        # ====================================================
        # SELL SCORE
        # ====================================================

        sell_score = 0

        if ema20_value < ema50_value:
            sell_score += 30

        if price < ema20_value:
            sell_score += 20

        if 30 < rsi_value < 50:
            sell_score += 25

        if momentum < 0:
            sell_score += 15

        if strength >= 30:
            sell_score += 10


        # ====================================================
        # SIGNAL DECISION
        # ====================================================

        confidence = max(
            buy_score,
            sell_score
        )

        if (
            buy_score >= 70
            and buy_score > sell_score
        ):

            signal = "🟢 BUY"

        elif (
            sell_score >= 70
            and sell_score > buy_score
        ):

            signal = "🔴 SELL"

        else:

            signal = "🟡 WAIT"


        # ====================================================
        # SIGNAL QUALITY
        # ====================================================

        if confidence >= 85:

            quality = "💎 VERY STRONG"

        elif confidence >= 70:

            quality = "🔥 STRONG"

        elif confidence >= 55:

            quality = "⚡ MEDIUM"

        else:

            quality = "⚠️ WEAK"


        return {

            "price": price,

            "ema20": ema20_value,

            "ema50": ema50_value,

            "rsi": rsi_value,

            "trend": trend,

            "strength": strength,

            "strength_text": strength_text,

            "volatility": volatility,

            "volatility_text": volatility_text,

            "momentum": momentum,

            "signal": signal,

            "confidence": confidence,

            "quality": quality,

            "buy_score": buy_score,

            "sell_score": sell_score,

            "support": support,

            "resistance": resistance,

        }


    except Exception as error:

        return {
            "error": str(error)
        }


# ============================================================
# FORMAT ANALYSIS
# ============================================================

def format_analysis(pair_name, time_button, result):

    if "error" in result:

        return (
            "⚠️ <b>MARKET ERROR</b>\n\n"
            f"{result['error']}"
        )


    now = datetime.now(UTC5).strftime(
        "%H:%M:%S"
    )


    return f"""
📈 <b>ULTIMATE MARKET ANALYSIS</b>

💱 <b>Pair:</b> {pair_name}

⏱ <b>Time:</b> {time_button}

🕐 <b>UTC+5:</b> {now}


💰 <b>Price:</b> {result['price']:.5f}


━━━━━━━━━━━━━━━━

📊 <b>EMA 20:</b> {result['ema20']:.5f}

📊 <b>EMA 50:</b> {result['ema50']:.5f}


📉 <b>RSI 14:</b> {result['rsi']:.2f}


🔥 <b>Trend:</b> {result['trend']}

💪 <b>Trend Strength:</b>

{result['strength_text']} ({result['strength']:.0f}%)


🌊 <b>Volatility:</b>

{result['volatility_text']}


⚡ <b>Momentum:</b>

{result['momentum']:.4f}%


━━━━━━━━━━━━━━━━

🎯 <b>Signal Confidence:</b>

{result['confidence']:.0f}%

{result['quality']}


🟢 <b>BUY Score:</b> {result['buy_score']}

🔴 <b>SELL Score:</b> {result['sell_score']}


━━━━━━━━━━━━━━━━

🚦 <b>MARKET BIAS:</b>

{result['signal']}


━━━━━━━━━━━━━━━━

📉 <b>Support:</b>

{result['support']:.5f}


📈 <b>Resistance:</b>

{result['resistance']:.5f}


━━━━━━━━━━━━━━━━

⚠️ <b>DISCLAIMER</b>

Bu tehniki bazar analizidir.
Netije kepillendirilen girdeji ýa-da
hökmany söwda netijesi däldir.

🕐 UTC+5 | TradeSignal AI
"""


# ============================================================
# STRONGEST SIGNAL
# ============================================================

def find_strongest_signal(timeframe="5m"):

    best_result = None

    best_pair_name = None

    best_symbol = None


    for pair_name, symbol in PAIRS.items():

        try:

            result = analyze_market(
                symbol,
                timeframe
            )

            if "error" in result:
                continue


            if result["signal"] == "🟡 WAIT":
                continue


            if (
                best_result is None
                or result["confidence"]
                > best_result["confidence"]
            ):

                best_result = result

                best_pair_name = pair_name

                best_symbol = symbol


        except Exception:

            continue


    if best_result is None:

        return None


    return {
        "pair_name": best_pair_name,
        "symbol": best_symbol,
        "result": best_result,
    }


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    get_user_config(user.id)


    await update.message.reply_text(

        f"""
🤖 <b>TradeSignal AI Ultimate</b>

Salam, {user.first_name}! 👋

📈 Professional market analysis
💱 Multiple Forex pairs
⏱ Multiple timeframes
🔥 Trend detection
📊 Technical indicators
🎯 Confidence system
🕐 UTC+5 timezone

Soňky mümkinçilikleriň birini saýla.
""",

        reply_markup=MENU,

        parse_mode="HTML"
    )


# ============================================================
# LIVE SIGNAL
# ============================================================

async def send_live_analysis(
    update,
    user_id
):

    config = get_user_config(user_id)


    await update.message.reply_text(
        "🔄 <b>Market analiz edilýär...</b>",
        parse_mode="HTML"
    )


    result = analyze_market(
        config["symbol"],
        config["timeframe"]
    )


    text = format_analysis(
        config["pair_name"],
        config["time_button"],
        result
    )


    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


    if "error" not in result:

        signal_history.append({

            "time": datetime.now(
                UTC5
            ).strftime("%H:%M:%S"),

            "pair": config["pair_name"],

            "timeframe": config["time_button"],

            "signal": result["signal"],

            "confidence": result["confidence"],

        })


        # Keep history limited

        if len(signal_history) > 30:

            signal_history.pop(0)


# ============================================================
# MENU HANDLER
# ============================================================

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:

        return


    user_id = update.effective_user.id

    message = update.message.text

    config = get_user_config(user_id)


    # ========================================================
    # LIVE SIGNALS
    # ========================================================

    if message == "📈 Live Signals":

        await send_live_analysis(
            update,
            user_id
        )


    # ========================================================
    # STRONGEST SIGNAL
    # ========================================================

    elif message == "🔥 Strongest Signal":

        await update.message.reply_text(
            "🔄 <b>Forex pairs analiz edilýär...</b>",
            parse_mode="HTML"
        )


        strongest = find_strongest_signal(
            config["timeframe"]
        )


        if strongest is None:

            await update.message.reply_text(
                """
🟡 <b>Soňky netije:</b>

Häzirki wagtda güýçli signal tapylmady.

Professional düzgün boýunça:
WAIT etmek has ygtybarly.
""",
                parse_mode="HTML"
            )

            return


        text = format_analysis(

            strongest["pair_name"],

            config["time_button"],

            strongest["result"]
        )


        await update.message.reply_text(
            "🔥 <b>STRONGEST MARKET SETUP</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            + text,
            parse_mode="HTML"
        )


    # ========================================================
    # SELECT PAIR
    # ========================================================

    elif message == "💱 Select Pair":

        await update.message.reply_text(
            "💱 <b>Currency pair saýla:</b>",
            reply_markup=PAIR_MENU,
            parse_mode="HTML"
        )


    # ========================================================
    # SELECT TIME
    # ========================================================

    elif message == "⏱ Select Time":

        await update.message.reply_text(
            """
⏱ <b>Timeframe saýla:</b>

⚠️ 5–30 SEC düwmeleri
iň täze elýeterli 1 MIN maglumatyna
esaslanýan gysga möhletli analizdir.
""",
            reply_markup=TIME_MENU,
            parse_mode="HTML"
        )


    # ========================================================
    # PAIR SELECTION
    # ========================================================

    elif message in PAIRS:

        config["pair_name"] = message

        config["symbol"] = PAIRS[message]


        await update.message.reply_text(

            f"""
✅ <b>Pair saýlandy!</b>

💱 {message}

Indi:

📈 Live Signals

basyp analiz edip bilersiň.
""",

            reply_markup=MENU,

            parse_mode="HTML"
        )


    # ========================================================
    # TIMEFRAME SELECTION
    # ========================================================

    elif message in TIMEFRAMES:

        config["time_button"] = message

        config["timeframe"] = TIMEFRAMES[message]


        await update.message.reply_text(

            f"""
✅ <b>Timeframe saýlandy!</b>

⏱ {message}

Indi 📈 Live Signals bas.
""",

            reply_markup=MENU,

            parse_mode="HTML"
        )


    # ========================================================
    # MARKET ANALYSIS
    # ========================================================

    elif message == "📊 Market Analysis":

        await send_live_analysis(
            update,
            user_id
        )


    # ========================================================
    # SIGNAL HISTORY
    # ========================================================

    elif message == "📜 Signal History":

        if not signal_history:

            await update.message.reply_text(

                "📜 <b>SIGNAL HISTORY</b>\n\n"
                "Heniz signal ýok.",

                parse_mode="HTML"
            )

            return


        history_text = (
            "📜 <b>SIGNAL HISTORY</b>\n\n"
        )


        for item in reversed(
            signal_history[-10:]
        ):

            history_text += (

                f"🕐 {item['time']}\n"

                f"💱 {item['pair']}\n"

                f"⏱ {item['timeframe']}\n"

                f"🚦 {item['signal']}\n"

                f"🎯 {item['confidence']:.0f}%\n"

                "━━━━━━━━━━━━\n"
            )


        await update.message.reply_text(
            history_text,
            parse_mode="HTML"
        )


    # ========================================================
    # SETTINGS
    # ========================================================

    elif message == "⚙️ Settings":

        await update.message.reply_text(

            f"""
⚙️ <b>SETTINGS</b>

💱 Pair:
{config['pair_name']}

⏱ Timeframe:
{config['time_button']}

🕐 Timezone:
UTC+5

📊 System:
EMA 20
EMA 50
RSI 14
Momentum
Volatility
Support
Resistance
Trend Strength
Confidence Score
""",

            parse_mode="HTML"
        )


    # ========================================================
    # HELP
    # ========================================================

    elif message == "❓ Help":

        await update.message.reply_text(

            """
❓ <b>TRADE SIGNAL AI HELP</b>

1️⃣ Currency pair saýla

2️⃣ Timef
