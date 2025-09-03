import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configura logging per debug
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Prendi i token dalle variabili di ambiente su Render
TOKEN = os.getenv("TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

# Funzione /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Pocket Option Signals Bot attivo!\nRiceverai segnali qui.")

# Funzione per controllare segnali (simulazione esempio BTC)
async def check_signals(app):
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=BTCUSD&interval=1min&apikey={ALPHA_KEY}"
        r = requests.get(url)
        data = r.json()

        last_refreshed = data["Meta Data"]["3. Last Refreshed"]
        last_close = float(data["Time Series (1min)"][last_refreshed]["4. close"])

        # Semplice logica UP / DOWN
        signal = "📈 BUY" if last_close % 2 == 0 else "📉 SELL"

        text = f"⚡ Segnale BTC/USD\nPrezzo: {last_close}\nSegnale: {signal}"

        # Invia a tutti (per semplicità mando al mio chat_id se startato)
        for chat_id in app.chat_ids:
            await app.bot.send_message(chat_id=chat_id, text=text)

    except Exception as e:
        logging.error(f"Errore check_signals: {e}")

# Salva le chat che usano /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    await update.message.reply_text("✅ Ti sei iscritto ai segnali Pocket Option!")

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Set dove salvo le chat_id
    subscribers = set()

    # Comandi
    app.add_handler(CommandHandler("start", save_chat_id))

    # Job: ogni 60 secondi controllo segnali
    app.job_queue.run_repeating(lambda _: check_signals(app), interval=60, first=5)

    print("✅ Bot avviato!")
    app.run_polling()
