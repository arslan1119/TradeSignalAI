import os
from datetime import datetime

import pandas as pd
import yfinance as yf

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)


TOKEN = os.getenv("BOT_TOKEN")

# =========================
# USER SETTINGS
# =========================

user_settings = {}
signal_history = []

PAIRS = {
    "🇪🇺 EUR/USD": "EURUSD=X",
    "🇬🇧 GBP/USD": "GBPUSD=X",
    "🇺🇸 USD/JPY": "JPY=X",
    "🇦🇺 AUD/USD": "AUDUSD=X",
    "🇪🇺 EUR/JPY": "EURJPY=X",
    "🇬🇧 GBP/JPY": "GBPJPY=X"
}

TIMEFRAMES = {
    "⏱ 5 SEC": "1m",
    "⏱ 10 SEC": "1m",
    "⏱ 15 SEC": "1m",
    "⏱ 30 SEC": "1m",
    "⏱ 1 MIN": "1m",
    "⏱ 5 MIN": "5m",
    "⏱ 10 MIN": "5m"
}


MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "🔥 Strongest Signal"],
        ["💱 Select Pair", "⏱ Select Time"],
        ["📊 Market Analytics", "📉 Trend Analysis"],
        ["📜 Signal History", "⚙️ Settings"],
        ["❓ Help"]
    ],
    resize_keyboard=True
)


TIME_MENU = ReplyKeyboardMarkup(
    [
        ["⏱ 5 SEC", "⏱ 10 SEC"],
        ["⏱ 15 SEC", "⏱ 30 SEC"],
        ["⏱ 1 MIN", "⏱ 5 MIN"],
        ["⏱ 10 MIN"],
        ["⬅️ Back"]
    ],
    resize_keyboard=True
)


PAIR_MENU = ReplyKeyboardMarkup(
    [
        ["🇪🇺 EUR/USD", "🇬🇧 GBP/USD"],
        ["🇺🇸 USD/JPY", "🇦🇺 AUD/USD"],
        ["🇪🇺 EUR/JPY", "🇬🇧 GBP/JPY"],
        ["⬅️ Back"]
    ],
    resize_keyboard=True
)


# =========================
# GET USER SETTINGS
# =========================

def get_user_config(user_id):

    if user_id not in user_settings:
        user_settings[user_id] = {
            "time_button": "⏱ 5 MIN",
            "timeframe": "5m",
            "pair_name": "🇪🇺 EUR/USD",
            "symbol": "EURUSD=X"
        }

    return user_settings[user_id]


# =========================
# MARKET ANALYSIS
# =========================

def analyze_market(symbol="EURUSD=X", timeframe="5m"):

    try:

        period = "5d"

        if timeframe == "1m":
            period = "1d"

        data = yf.download(
            symbol,
            period=period,
            interval=timeframe,
            progress=False,
            auto_adjust=False
        )

        if data.empty:
            return {
                "error": "Bazardan maglumat alyp bolmady."
            }

        close = data["Close"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        close = close.dropna()

        if len(close) < 55:
            return {
                "error": "Analiz üçin maglumat ýeterlik däl."
            }

        # EMA 20
        ema20 = close.ewm(
            span=20,
            adjust=False
        ).mean()

        # EMA 50
        ema50 = close.ewm(
            span=50,
            adjust=False
        ).mean()

        # RSI 14
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(
            window=14
        ).mean()

        avg_loss = loss.rolling(
            window=14
        ).mean()

        rs = avg_gain / avg_loss

        rsi = 100 - (
            100 / (1 + rs)
        )

        # Latest values
        price = float(close.iloc[-1])
        ema20_value = float(ema20.iloc[-1])
        ema50_value = float(ema50.iloc[-1])
        rsi_value = float(rsi.iloc[-1])

        # =========================
        # TREND
        # =========================

        if ema20_value > ema50_value:
            trend = "📈 UP TREND"
        elif ema20_value < ema50_value:
            trend = "📉 DOWN TREND"
        else:
            trend = "↔️ SIDEWAYS"

        # =========================
        # TREND STRENGTH
        # =========================

        ema_difference = abs(
            ema20_value - ema50_value
        )

        percentage_difference = (
            ema_difference / price
        ) * 100

        strength = min(
            100,
            int(percentage_difference * 10000)
        )

        if strength < 30:
            strength_text = "🟡 WEAK"
        elif strength < 60:
            strength_text = "🟠 MEDIUM"
        else:
            strength_text = "🟢 STRONG"

        # =========================
        # SIGNAL
        # =========================

        score = 0
        signal = "🟡 WAIT"

        # BUY conditions
        if ema20_value > ema50_value:
            score += 35

        if 50 < rsi_value < 70:
            score += 35

        if price > ema20_value:
            score += 20

        buy_score = score

        # SELL score
        sell_score = 0

        if ema20_value < ema50_value:
            sell_score += 35

        if 30 < rsi_value < 50:
            sell_score += 35

        if price < ema20_value:
            sell_score += 20

        # Final signal
        confidence = max(
            buy_score,
            sell_score
        )

        if buy_score >= 60:
            signal = "🟢 BUY"

        elif sell_score >= 60:
            signal = "🔴 SELL"

        else:
            signal = "🟡 WAIT"

        # =========================
        # SUPPORT / RESISTANCE
        # =========================

        recent_data = close.tail(20)

        support = float(recent_data.min())
        resistance = float(recent_data.max())

        return {
            "price": price,
            "ema20": ema20_value,
            "ema50": ema50_value,
            "rsi": rsi_value,
            "trend": trend,
            "strength": strength,
            "strength_text": strength_text,
            "signal": signal,
            "confidence": confidence,
            "support": support,
            "resistance": resistance
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================
# CREATE ANALYSIS TEXT
# =========================

def create_analysis(pair_name, result, timeframe_name):

    if "error" in result:
        return f"❌ Error: {result['error']}"

    return f"""
📈 <b>PROFESSIONAL MARKET ANALYSIS</b>

💱 <b>Pair:</b> {pair_name}
⏱ <b>Time:</b> {timeframe_name}

💰 <b>Price:</b> {result['price']:.5f}

📊 <b>EMA 20:</b> {result['ema20']:.5f}
📊 <b>EMA 50:</b> {result['ema50']:.5f}

📉 <b>RSI 14:</b> {result['rsi']:.2f}

🔥 <b>Trend:</b> {result['trend']}

💪 <b>Trend Strength:</b>
{result['strength_text']} ({result['strength']}%)

🎯 <b>Signal Confidence:</b>
{result['confidence']}%

🟢🔴 <b>SIGNAL:</b>
<b>{result['signal']}</b>

━━━━━━━━━━━━━━

📉 <b>Support:</b> {result['support']:.5f}

📈 <b>Resistance:</b> {result['resistance']:.5f}

⚠️ Bu diňe tehniki bazar analizi.
⚠️ Signal kepillendirilen netije däldir.
"""


# =========================
# FIND STRONGEST SIGNAL
# =========================

def find_best_signal(timeframe="5m"):

    results = []

    for pair_name, symbol in PAIRS.items():

        result = analyze_market(
            symbol,
            timeframe
        )

        if "error" not in result:

            results.append({
                "pair": pair_name,
                "symbol": symbol,
                "result": result
            })

    if not results:
        return "❌ Güýçli signal tapmak üçin maglumat alyp bolmady."

    # Sort by confidence
    results.sort(
        key=lambda x: x["result"]["confidence"],
        reverse=True
    )

    best = results[0]

    result = best["result"]

    return f"""
🔥 <b>STRONGEST MARKET SIGNAL</b>

🏆 <b>Best Pair:</b> {best['pair']}

💰 <b>Price:</b> {result['price']:.5f}

📈 <b>Trend:</b>
{result['trend']}

💪 <b>Strength:</b>
{result['strength_text']} ({result['strength']}%)

🎯 <b>Confidence:</b>
{result['confidence']}%

🚨 <b>BEST SIGNAL:</b>

<b>{result['signal']}</b>

📊 EMA 20: {result['ema20']:.5f}
📊 EMA 50: {result['ema50']:.5f}
📉 RSI: {result['rsi']:.2f}

⚠️ Bu diňe tehniki analizdir.
"""


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    text = f"""
🤖 <b>TradeSignal AI PRO</b>

Salam, {user.first_name}! 👋

📈 Professional market analysis
🔥 Strongest signal scanner
📊 EMA + RSI analysis
💱 Multi-pair scanner
⏱ Timeframe selection
📉 Support & Resistance

Soňky mümkinçilikleriň birini saýla.
"""

    await update.message.reply_text(
        text,
        reply_markup=MENU,
        parse_mode="HTML"
    )


# =========================
# MENU HANDLER
# =========================

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message.text

    user_id = update.effective_user.id

    config = get_user_config(user_id)

    # BACK
    if message == "⬅️ Back":

        await update.message.reply_text(
            "🏠 Main menu",
            reply_markup=MENU
        )

        return


    # =========================
    # SELECT TIME
    # =========================

    if message == "⏱ Select Time":

        await update.message.reply_text(
            "⏱ <b>Wagt interwaly saýla:</b>",
            reply_markup=TIME_MENU,
            parse_mode="HTML"
        )

        return


    # =========================
    # TIMEFRAME SELECTED
    # =========================

    if message in TIMEFRAMES:

        config["time_button"] = message
        config["timeframe"] = TIMEFRAMES[message]

        await update.message.reply_text(
            f"""
✅ <b>Timeframe saýlandy!</b>

⏱ {message}

📈 Indi <b>Live Signals</b> düwmesine bas.
""",
            reply_markup=MENU,
            parse_mode="HTML"
        )

        return


    # =========================
    # SELECT PAIR
    # =========================

    if message == "💱 Select Pair":

        await update.message.reply_text(
            "💱 <b>Currency Pair saýla:</b>",
            reply_markup=PAIR_MENU,
            parse_mode="HTML"
        )

        return


    # =========================
    # PAIR SELECTED
    # =========================

    if message in PAIRS:

        config["pair_name"] = message
        config["symbol"] = PAIRS[message]

        await update.message.reply_text(
            f"""
✅ <b>Pair saýlandy!</b>

💱 {message}

📈 Indi Live Signals düwmesine bas.
""",
            reply_markup=MENU,
            parse_mode="HTML"
        )

        return


    # =========================
    # LIVE SIGNAL
    # =========================

    if message == "📈 Live Signals":

        result = analyze_market(
            config["symbol"],
            config["timeframe"]
        )

        analysis = create_analysis(
            config["pair_name"],
            result,
            config["time_button"]
        )

        if "error" not in result:

            signal_history.append({
                "pair": config["pair_name"],
                "signal": result["signal"],
                "confidence": result["confidence"],
                "time": datetime.now().strftime("%H:%M")
            })

            # Keep last 10 signals
            if len(signal_history) > 10:
                signal_history.pop(0)

        await update.message.reply_text(
            analysis,
            parse_mode="HTML"
        )

        return


    # =========================
    # STRONGEST SIGNAL
    # =========================

    if message == "🔥 Strongest Signal":

        await update.message.reply_text(
            "🔍 Market scanner işleýär..."
        )

        analysis = find_best_signal(
            config["timeframe"]
        )

        await update.message.reply_text(
            analysis,
            parse_mode="HTML"
        )

        return


    # =========================
    # MARKET ANALYTICS
    # =========================

    if message == "📊 Market Analytics":

        await update.message.reply_text(
            """
📊 <b>MARKET ANALYTICS</b>

📈 Trend analysis
📊 EMA 20 & EMA 50
📉 RSI 14
🎯 Signal confidence
📉 Support & Resistance
🔥 Trend strength

💡 Pair we timeframe saýlap,
Live Signals bas.
""",
            parse_mode="HTML"
        )

        return


    # =========================
    # TREND ANALYSIS
    # =========================

    if message == "📉 Trend Analysis":

        result = analyze_market(
            config["symbol"],
            config["timeframe"]
        )

        if "error" in result:

            await update.message.reply_text(
                f"❌ {result['error']}"
            )

            return

        await update.message.reply_text(
            f"""
📉 <b>TREND ANALYSIS</b>

💱 {config['pair_name']}

🔥 Trend:
<b>{result['trend']}</b>

💪 Strength:
{result['strength_text']}

📊 EMA 20:
{result['ema20']:.5f}

📊 EMA 50:
{result['ema50']:.5f}

📉 RSI:
{result['rsi']:.2f}
""",
            parse_mode="HTML"
        )

        return


    # =========================
    # SIGNAL HISTORY
    # =========================

    if message == "📜 Signal History":

        if not signal_history:

            await update.message.reply_text(
                "📜 <b>SIGNAL HISTORY</b>\n\nHeniz signal ýok.",
                parse_mode="HTML"
            )

            return

        history_text = "📜 <b>SIGNAL HISTORY</b>\n\n"

        for item in reversed(signal_history):

            history_text += (
                f"💱 {item['pair']}\n"
                f"🎯 {item['signal']}\n"
                f"📊 Confidence: {item['confidence']}%\n"
                f"🕒 {item['time']}\n\n"
            )

        await update.message.reply_text(
            history_text,
            parse_mode="HTML"
        )

        return


    # =========================
    # SETTINGS
    # =========================

    if message == "⚙️ Settings":

        await update.message.reply_text(
            f"""
⚙️ <b>SETTINGS</b>

💱 Current Pair:
{config['pair_name']}

⏱ Current Time:
{config['time_button']}

📊 Analysis:
EMA 20 + EMA 50 + RSI 14

🎯 Signal Filter:
Confidence system active

Use:
💱 Select Pair
⏱ Select Time
""",
            parse_mode="HTML"
        )

        return


    # =========================
    # HELP
    # =========================

    if message == "❓ Help":

        await update.message.reply_text(
            """
❓ <b>TRADE SIGNAL AI PRO HELP</b>

1️⃣ 💱 Select Pair
Currency pair saýla.

2️⃣ ⏱ Select Time
Wagt interwaly saýla.

3️⃣ 📈 Live Signals
Soňky market analizini al.

4️⃣ 🔥 Strongest Signal
Birnäçe pair-i deňeşdirýär.

5️⃣ 📉 Trend Analysis
Trend güýjüni görkezýär.

⚠️ Bu bot diňe tehniki analiz berýär.
⚠️ Trading risklidir.
""",
            parse_mode="HTML"
        )

        return


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(f"ERROR: {context.error}")


# =========================
# RUN BOT
# =========================

def main():

    if not TOKEN:
        print("❌ BOT_TOKEN tapylmady!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_handler
        )
    )

    app.add_error_handler(error_handler)

    print("🤖 TradeSignal AI PRO started!")

    app.run_polling()


if __name__ == "__main__":
    main()
