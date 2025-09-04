import os
import logging
import requests
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

subscribers = set()
user_assets = {}

# ==== FUNZIONI DATI ====
def get_binance_prices(symbol="BTCUSDT", limit=50):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}"
        data = requests.get(url, timeout=10).json()
        return [float(c[4]) for c in data]
    except Exception as e:
        logging.error(f"Errore Binance {symbol}: {e}")
        return []

def get_alpha_prices(symbol="EURUSD", limit=50):
    try:
        url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval=1min&apikey={ALPHA_KEY}&outputsize=compact"
        data = requests.get(url, timeout=10).json()
        if "Time Series FX (1min)" not in data:
            return []
        prices = [float(v["4. close"]) for k,v in data["Time Series FX (1min)"].items()]
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
    now = datetime.now()
    entry_time = (now + timedelta(minutes=2)).strftime("%H:%M")
    return f"📊 Segnale Pocket Option\nAsset: {asset}\nDirezione: {signal}\nOra ingresso: {entry_time}\nTimeframe: 1m | 2m | 5m"

# ==== BROADCAST LOOP ====
async def broadcast_loop(app):
    while True:
        if subscribers:
            for user_id in list(subscribers):
                asset = user_assets.get(user_id)
                if not asset:
                    continue
                prices = get_binance_prices(asset) if "USDT" in asset else get_alpha_prices(asset)
                signal = generate_signal(prices)
                msg = format_message(asset, signal)
                try:
                    await app.bot.send_message(chat_id=user_id, text=msg)
                except Exception as e:
                    logging.error(f"Errore inviando a {user_id}: {e}")
        await asyncio.sleep(300)

# ==== HANDLER BOT ====
async def start(update, context):
    user_id = update.effective_chat.id
    subscribers.add(user_id)

    keyboard = [
        [InlineKeyboardButton("BTCUSDT", callback_data="BTCUSDT"),
         InlineKeyboardButton("ETHUSDT", callback_data="ETHUSDT")],
        [InlineKeyboardButton("BNBUSDT", callback_data="BNBUSDT"),
         InlineKeyboardButton("EURUSD", callback_data="EURUSD")],
        [InlineKeyboardButton("GBPJPY", callback_data="GBPJPY"),
         InlineKeyboardButton("USDJPY", callback_data="USDJPY")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Sei iscritto!\n\nScegli un asset dai bottoni qui sotto 👇\nRiceverai segnali automatici ogni 5 minuti.", reply_markup=reply_markup)

async def stop(update, context):
    user_id = update.effective_chat.id
    subscribers.discard(user_id)
    user_assets.pop(user_id, None)
    await update.message.reply_text("🛑 Hai interrotto i segnali. Puoi riattivarli con /start.")

async def button(update, context):
    query = update.callback_query
    await query.answer()
    asset = query.data
    user_id = query.from_user.id
    user_assets[user_id] = asset
    await query.edit_message_text(text=f"✅ Asset aggiornato a {asset}\nRiceverai segnali automatici ogni 5 minuti.")

# ==== MAIN ====
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(button))

    await app.initialize()
    await app.start()
    asyncio.create_task(broadcast_loop(app))
    await app.updater.start_polling()  # per compatibilità con run_polling
    await app.updater.idle()
    await app.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
