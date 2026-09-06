import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

MENU = ReplyKeyboardMarkup(
    [
        ["📈 Live Signals", "📊 Market Analytics"],
        ["📜 Signal History", "💎 Premium"],
        ["⚙️ Settings", "❓ Help"],
    ],
    resize_keyboard=True,
)


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
        await update.message.reply_text(
            "📈 <b>LIVE SIGNALS</b>\n\n"
            "🔍 Bazar analizi entek birikdirilmedi.\n"
            "Indiki ädimde EMA, RSI we trend analizini goşarys.",
            parse_mode="HTML"
        )

    elif message == "📊 Market Analytics":
        await update.message.reply_text(
            "📊 <b>MARKET ANALYTICS</b>\n\n"
            "📈 Trend analysis\n"
            "📊 Technical indicators\n"
            "📉 Support & Resistance\n"
            "📰 Market filters",
            parse_mode="HTML"
        )

    elif message == "📜 Signal History":
        await update.message.reply_text(
            "📜 <b>SIGNAL HISTORY</b>\n\n"
            "Soňky signallaryň statistikasy soň goşular.",
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
