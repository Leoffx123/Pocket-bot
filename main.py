import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

subscribers = set()
user_assets = {}

asset_map = {
    "Bitcoin": "BTCUSDT",
    "Ethereum": "ETHUSDT",
    "EUR/USD": "EURUSD",
    "GBP/USD": "GBPUSD"
    # aggiungi altri asset come vuoi
}

# FUNZIONI DATI
def get_binance_prices(symbol="BTCUSDT", limit=50):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}"
        data = requests.get(url, timeout=5).json()
        return [float(c[4]) for c in data]
    except Exception as e:
        logging.error(f"Errore Binance {symbol}: {e}")
        return []

def get_alpha_prices(symbol="EURUSD", limit=50):
    try:
        url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval=1min&apikey={ALPHA_KEY}&outputsize=compact"
        data = requests.get(url, timeout=5).json()
        if "Time Series FX (1min)" not in data:
            return []
        return [float(v["4. close"]) for _, v in data["Time Series FX (1min)"].items()][:limit][::-1]
    except Exception as e:
        logging.error(f"Errore Alpha {symbol}: {e}")
        return []

def generate_signal(prices: list):
    if len(prices) < 20:
        return "⏳ Dati insufficienti"
    df = pd.DataFrame(prices, columns=["close"])
    df["EMA5"] = df["close"].ewm(span=5).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    return "📈 UP" if df["EMA5"].iloc[-1] > df["EMA20"].iloc[-1] else "📉 DOWN"

def format_message(asset, signal):
    tz = pytz.timezone("Europe/Rome")
    now = datetime.now(tz)
    entry_time = (now + timedelta(minutes=2)).strftime("%H:%M")
    return f"📊 Segnale Pocket Option\nAsset: {asset}\nDirezione: {signal}\nOra ingresso: {entry_time}\nTimeframe: 1m | 2m | 5m"

# HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    subscribers.add(user_id)

    buttons = [[InlineKeyboardButton(asset, callback_data=asset)] for asset in asset_map.keys()]
    reply_markup = InlineKeyboardMarkup(buttons)

    # avvia job solo una volta
    if not hasattr(context.application, "job_started"):
        context.application.job_queue.run_repeating(auto_broadcast, interval=300, first=5)
        context.application.job_started = True

    await update.message.reply_text("✅ Sei iscritto! Scegli un asset 👇", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_assets[query.message.chat.id] = query.data
    await query.edit_message_text(f"✅ Asset aggiornato a {query.data}\nRiceverai segnali ogni 5 minuti.")

async def auto_broadcast(context: ContextTypes.DEFAULT_TYPE):
    for user_id in list(subscribers):
        asset_name = user_assets.get(user_id)
        if not asset_name:
            continue
        ticker = asset_map[asset_name]
        prices = get_binance_prices(ticker) if ticker.endswith("USDT") else get_alpha_prices(ticker)
        signal = generate_signal(prices)
        msg = format_message(asset_name, signal)
        try:
            await context.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logging.error(f"Errore inviando a {user_id}: {e}")

# MAIN
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.job_queue.run_repeating(auto_broadcast, interval=300, first=5)
    app.run_polling()  # NON usare updater, NON usare asyncio.run

if __name__ == "__main__":
    main()
