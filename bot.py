import os
import yfinance as yf
from datetime import datetime
import pandas as pd

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
signal_history = []
MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "📊 Market Analytics"],
        ["📜 Signal History", "💎 Premium"],
        ["⚙️ Settings", "❓ Help"],
    ],
    resize_keyboard=True,
)

def analyze_market(symbol="EURUSD=X"):
    try:
        data = yf.download(
            symbol,
            period="5d",
            interval="5m",
            progress=False
        )

        if data.empty:
            return "❌ Bazardan maglumat alyp bolmady."

        close = data["Close"]

        if hasattr(close, "columns"):
            close = close.iloc[:, 0]

        # EMA 20
        ema20 = close.ewm(span=20, adjust=False).mean()

        # EMA 50
        ema50 = close.ewm(span=50, adjust=False).mean()

        # RSI 14
        delta = close.diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Latest values
        price = float(close.iloc[-1])
        ema20_value = float(ema20.iloc[-1])
        ema50_value = float(ema50.iloc[-1])
        rsi_value = float(rsi.iloc[-1])

        # Trend
        if ema20_value > ema50_value:
            trend = "📈 UP TREND"
        elif ema20_value < ema50_value:
            trend = "📉 DOWN TREND"
        else:
            trend = "➡️ SIDEWAYS"

        # Signal
        if trend == "📈 UP TREND" and rsi_value < 70:
            signal = "🟢 BUY"
        elif trend == "📉 DOWN TREND" and rsi_value > 30:
            signal = "🔴 SELL"
        else:
            signal = "🟡 WAIT"

    signal_history.append({
    "symbol": symbol,
    "signal": signal,
    "price": price,
    "trend": trend,
    "time": datetime.now().strftime("%H:%M")
    })

    # diňe soňky 10 signal saklanýar
    if len(signal_history) > 10:
    signal_history.pop(0)
        return f"""
    📈 <b>LIVE MARKET ANALYSIS</b>

    💱 Pair: <b>{symbol}</b>
    💰 Price: <b>{price:.5f}</b>

    📊 EMA 20: <b>{ema20_value:.5f}</b>
    📊 EMA 50: <b>{ema50_value:.5f}</b>

    📉 RSI 14: <b>{rsi_value:.2f}</b>

    🔥 Trend: <b>{trend}</b>

    🎯 Signal: <b>{signal}</b>

    ⚠️ Bu diňe maglumatlaýyn bazar analizi.
    """

    except Exception as e:
        return f"❌ Error: {str(e)}"
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = f"""
🤖 <b>TradeSignal AI</b>

Salam, {user.first_name}! 👋

📊 Professional market analysis
📈 Trading signal dashboard
🤖 AI-powered filters
🕐 UTC+5 timezone
💎 Premium features

Soňky mümkinçilikleriň birini saýla.
"""

    await update.message.reply_text(
        text,
        reply_markup=MENU,
        parse_mode="HTML"
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    
    if message == "📈 Live Signals":
        analysis = analyze_market("EURUSD=X")

        await update.message.reply_text(
            analysis,
            parse_mode="HTML"
        )

    elif message == "📊 Market Analytics":
        await update.message.reply_text(
            "📊 <b>MARKET ANALYTICS</b>\n\n"
            "📈 Trend analysis\n"
            "📊 Technical indicators\n"
            "📉 Support & Resistance\n"
            "🗺️ Market filters",
            parse_mode="HTML"
        )

    elif message == "📜 Signal History":

    if not signal_history:
        await update.message.reply_text(
            "📜 <b>SIGNAL HISTORY</b>\n\n"
            "Heniz signal ýok.\n\n"
            "📈 Live Signals düwmesine basyp ilkinji analizi başlat.",
            parse_mode="HTML"
        )

    else:
        history_text = "📜 <b>SIGNAL HISTORY</b>\n\n"

        for item in reversed(signal_history):
            history_text += (
                f"💱 <b>{item['symbol']}</b>\n"
                f"🎯 Signal: <b>{item['signal']}</b>\n"
                f"💰 Price: <b>{item['price']:.5f}</b>\n"
                f"🔥 Trend: <b>{item['trend']}</b>\n"
                f"🕒 Time: {item['time']}\n"
                "━━━━━━━━━━━━━━\n"
            )

        await update.message.reply_text(
            history_text,
            parse_mode="HTML"
        )

    elif message == "💎 Premium":
        await update.message.reply_text(
            "💎 <b>PREMIUM</b>\n\n"
            "✨ Advanced analysis\n"
            "🔔 More notifications\n"
            "📊 Extended statistics\n"
            "🤖 Advanced signal filters",
            parse_mode="HTML"
        )

    elif message == "⚙️ Settings":
        await update.message.reply_text(
            "⚙️ <b>SETTINGS</b>\n\n"
            "🕐 Timezone: UTC+5\n"
            "🔔 Notifications\n"
            "🌐 Language\n"
            "🛡️ Risk settings",
            parse_mode="HTML"
        )

    elif message == "❓ Help":
        await update.message.reply_text(
            "❓ <b>HELP</b>\n\n"
            "TradeSignal AI — bazar maglumatlaryny we "
            "tehniki indikatorlary analiz etmek üçin döredilýär.\n\n"
            "⚠️ Söwda töwekgelçiliklidir. Netije kepillendirilmeýär.",
            parse_mode="HTML"
        )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN tapylmady!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)
    )

    print("🤖 TradeSignal AI started!")

    app.run_polling()


if __name__ == "__main__":
    main()
