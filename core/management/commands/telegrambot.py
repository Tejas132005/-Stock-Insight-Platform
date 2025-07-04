import os
import logging
import time
import uuid
import numpy as np

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import TelegramUser, Prediction
from django.utils.timezone import now
from core.predictions.utils import fetch_data, preprocess
from core.predictions.model_loader import get_model
from core.predictions.plotter import plot_history, plot_prediction
from asgiref.sync import sync_to_async

# Rate limiting store
RATE_LIMIT = {}

# Logging
logger = logging.getLogger("telegrambot")
logging.basicConfig(level=logging.INFO)

class Command(BaseCommand):
    help = "Run Telegram Bot"

    def handle(self, *args, **kwargs):
        TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        if not TOKEN:
            self.stderr.write("Missing TELEGRAM_BOT_TOKEN env variable.")
            return

        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("predict", self.predict))
        app.add_handler(CommandHandler("latest", self.latest))
        app.add_handler(CommandHandler("help", self.help))

        logger.info("🤖 Telegram Bot Started")
        app.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        username = update.effective_user.username

        try:
            user = await sync_to_async(User.objects.get)(username=username)
            await sync_to_async(TelegramUser.objects.update_or_create)(user=user, defaults={"chat_id": chat_id})
            await update.message.reply_text("✅ Telegram linked with your account.")
        except User.DoesNotExist:
            await update.message.reply_text("❌ User not found. Register on the platform first.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "/start → Link your Telegram\n"
            "/predict <TICKER> → Predict stock price\n"
            "/latest → Show latest prediction\n"
            "/help → Show help"
        )

    async def latest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        try:
            tg_user = await sync_to_async(TelegramUser.objects.get)(chat_id=chat_id)
            prediction = await sync_to_async(
                lambda: Prediction.objects.filter(user=tg_user.user).latest("created_at")
            )()
            await update.message.reply_text(
                f"📈 Ticker: {prediction.ticker}\n"
                f"Predicted Price: ₹{prediction.next_day_price:.2f}\n"
                f"Date: {prediction.created_at.date()}"
            )
        except TelegramUser.DoesNotExist:
            await update.message.reply_text("⚠️ Please link your Telegram using /start")
        except Prediction.DoesNotExist:
            await update.message.reply_text("❌ No predictions found.")

    async def predict(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        try:
            tg_user = await sync_to_async(TelegramUser.objects.select_related('user').get)(chat_id=chat_id)
            user_id = tg_user.user.id  # This works because select_related prefetches user
            user = tg_user.user
        except TelegramUser.DoesNotExist:
            await update.message.reply_text("⚠️ Please link your Telegram using /start")
            return

        # Rate limit check
        current_time = time.time()
        user_key = str(user_id)
        timestamps = RATE_LIMIT.get(user_key, [])
        timestamps = [t for t in timestamps if current_time - t < 60]
        if len(timestamps) >= 10:
            await update.message.reply_text("⚠️ Rate limit exceeded (10 predictions/min)")
            return
        timestamps.append(current_time)
        RATE_LIMIT[user_key] = timestamps

        # Validate args
        if len(context.args) != 1:
            await update.message.reply_text("❌ Usage: /predict <TICKER>")
            return

        ticker = context.args[0].upper()

        try:
            logger.info(f"Fetching data for {ticker}")
            df = fetch_data(ticker)
            X, y, scaler = preprocess(df)
            model = get_model()
            preds = model.predict(X)
            next_price = scaler.inverse_transform(preds)[-1][0]
            y_true = scaler.inverse_transform(y)
            y_pred = scaler.inverse_transform(preds)

            plot1 = f"media/{uuid.uuid4()}_history.png"
            plot2 = f"media/{uuid.uuid4()}_compare.png"
            plot_history(df, plot1)
            plot_prediction(y_true, y_pred, plot2)

            prediction = await sync_to_async(Prediction.objects.create)(
                user=user,
                ticker=ticker,
                next_day_price=next_price,
                metrics={
                    "mse": float(np.mean((y_true - y_pred) ** 2)),
                    "rmse": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
                    "r2": float(1 - (np.sum((y_true - y_pred)**2) / np.sum((y_true - y_true.mean())**2)))
                },
                plot1_url=plot1,
                plot2_url=plot2
            )

            await update.message.reply_text(f"✅ Predicted price for {ticker}: ₹{next_price:.2f}")
            await context.bot.send_photo(chat_id=chat_id, photo=open(plot1, "rb"))
            await context.bot.send_photo(chat_id=chat_id, photo=open(plot2, "rb"))
        except Exception as e:
            logger.exception(f"Prediction failed for {ticker}: {e}")
            await update.message.reply_text("❌ Prediction failed. Try again.")