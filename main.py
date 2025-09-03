import os
import logging
import requests
import pandas as pd
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Carica variabili ambiente (.env)
load_dotenv()
TOKEN = os.getenv("TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Lista utenti iscritti
subscribers = set()


# ========= FUNZIONI BOT ========= #

# /start -> iscrive utente
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    subscribers.add(user_id)
    await update.message.reply_text("✅ Sei iscritto ai segnali di Pocket Option!")

# /stop -> disiscrive utente
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    subscribers.discard(user_id)
    await update.message.reply_text("❌ Sei stato rimosso dai segnali.")

# Funzione che simula il calcolo dei segnali
def generate_signal(symbol="BTCUSDT"):
    # Puoi sostituire questa parte con logica tecnica vera
    decision = np.random.choice(["UP", "DOWN"])
    return f"📊 Segnale per {symbol}: {decision}"

# /signal -> invia un segnale manualmente
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = "BTCUSDT"
    sig = generate_signal(symbol)
    await update.message.reply_text(sig)

# /broadcast -> invia segnale a tutti gli iscritti
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = "BTCUSDT"
    sig = generate_signal(symbol)

    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=sig)
        except Exception as e:
            logging.error(f"Errore inviando a {user_id}: {e}")


# ========= AVVIO BOT ========= #

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.run_polling()


if __name__ == "__main__":
    main()
