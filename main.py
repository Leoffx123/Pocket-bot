import os
import logging
import requests
import pandas as pd
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Carica le variabili da .env (su Railway le setti nelle "Variables")
load_dotenv()
TOKEN = os.getenv("TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

# Configura logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Lista iscritti (multi-user)
subscribers = set()

# Funzione per calcolare RSI
def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# Ottieni dati da Alpha Vantage
def fetch_data(symbol="EURUSD", interval="1min"):
    url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval={interval}&apikey={ALPHA_KEY}&datatype=json"
    r = requests.get(url)
    data = r.json()
    if "Time Series FX (1min)" not in data:
        return None
    df = pd.DataFrame(data["Time Series FX (1min)"]).T.astype(float)
    df = df.rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close"
    })
    return df

# Genera segnale RSI
def get_signal(symbol="EURUSD"):
    df = fetch_data(symbol)
    if df is None:
        return None
    rsi = compute_rsi(df["close"])
    if rsi < 30:
        return f"📉 SELL Signal on {symbol} (RSI={rsi:.2f})"
    elif rsi > 70:
        return f"📈 BUY Signal on {symbol} (RSI={rsi:.2f})"
    else:
        return None

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    await update.message.reply_text("✅ Sei iscritto ai segnali Pocket Option!")

# /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.discard(chat_id)
    await update.message.reply_text("❌ Sei stato rimosso dai segnali.")

# Controllo segnali e invio
async def check_signals(app):
    symbols = ["EURUSD", "GBPJPY", "BTCUSD"]  # puoi aggiungere altri qui
    for sym in symbols:
        signal = get_signal(sym)
        if signal:
            for chat_id in subscribers:
                try:
                    await app.bot.send_message(chat_id, signal)
                except Exception as e:
                    logging.error(f"Errore invio a {chat_id}: {e}")

# Main
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))

    job_queue = app.job_queue
    job_queue.run_repeating(lambda _: check_signals(app), interval=60, first=5)

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
