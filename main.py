import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# ================== CONFIG ================== #
load_dotenv()
TOKEN = os.getenv("TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

subscribers = set()
user_assets = {}

# ================== ASSET MAP ================== #
asset_map = {
    "Bitcoin": "BTCUSDT",
    "Ethereum": "ETHUSDT",
    "Binance Coin": "BNBUSDT",
    "Solana": "SOLUSDT",
    "XRP": "XRPUSDT",
    "Dogecoin": "DOGEUSDT",
    "Cardano": "ADAUSDT",
    "Avalanche": "AVAXUSDT",
    "Polkadot": "DOTUSDT",
    "Polygon": "MATICUSDT",
    "Litecoin": "LTCUSDT",
    "Shiba Inu": "SHIBUSDT",
    "Tron": "TRXUSDT",
    "Chainlink": "LINKUSDT",
    "Aptos": "APTUSDT",
    "Cosmos": "ATOMUSDT",
    "Near Protocol": "NEARUSDT",
    "Filecoin": "FILUSDT",
    "Internet Computer": "ICPUSDT",
    "Uniswap": "UNIUSDT",
    "EUR/USD": "EURUSD",
    "GBP/USD": "GBPUSD",
    "USD/JPY": "USDJPY",
    "GBP/JPY": "GBPJPY",
    "EUR/JPY": "EURJPY"
}

# ================== FUNZIONI DATI ================== #
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
        url = (
            f"https://www.alphavantage.co/query?function=FX_INTRADAY"
            f"&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}"
            f"&interval=1min&apikey={ALPHA_KEY}&outputsize=compact"
        )
        data = requests.get(url, timeout=5).json()
        if "Time Series FX (1min)" not in data:
            return []
        prices = [float(v["4. close"]) for _, v in data["Time Series FX (1min)"].items()]
        return prices[:limit][::-1]
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
    return (
        f"📊 Segnale Pocket Option\n"
        f"Asset: {asset}\n"
        f"Direzione: {signal}\n"
        f"Ora ingresso: {entry_time}\n"
        f"Timeframe: 1m | 2m | 5m"
    )

# ================== HANDLERS ================== #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    subscribers.add(user_id)

    buttons, row = [], []
    for i, asset in enumerate(asset_map.keys(), start=1):
        row.append(InlineKeyboardButton(asset, callback_data=asset))
        if i % 4 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "✅ Sei iscritto!\n\nScegli un asset 👇\nIl bot ti manderà segnali reali ogni 5 minuti.",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    asset_name = query.data
    user_id = query.message.chat.id
    user_assets[user_id] = asset_name
    await query.edit_message_text(f"✅ Asset aggiornato a {asset_name}\nRiceverai segnali ogni 5 minuti.")

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

# ================== MAIN ================== #
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # qui la job_queue funziona perché lanciata dentro run_polling
    app.job_queue.run_repeating(auto_broadcast, interval=300, first=20)

    app.run_polling()

if __name__ == "__main__":
    main()
