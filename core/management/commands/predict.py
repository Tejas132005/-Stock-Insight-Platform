from django.core.management.base import BaseCommand, CommandError
from core.predictions.utils import fetch_data, preprocess
from core.predictions.model_loader import get_model
from core.predictions.plotter import plot_history, plot_prediction
from core.models import Prediction
from django.contrib.auth.models import User

from decouple import config
import numpy as np
import uuid
import os


class Command(BaseCommand):
    help = "Make stock predictions using the pre-trained LSTM model."

    def add_arguments(self, parser):
        parser.add_argument('--ticker', type=str, help='Stock ticker (e.g., AAPL)')
        parser.add_argument('--all', action='store_true', help='Predict for all tickers in the DB')

    def handle(self, *args, **options):
        tickers = []

        if options['ticker']:
            tickers = [options['ticker'].upper()]
        elif options['all']:
            tickers = Prediction.objects.values_list('ticker', flat=True).distinct()
        else:
            raise CommandError("You must pass either --ticker <TICKER> or --all")

        model = None

        try:
            model = get_model()
        except Exception as e:
            raise CommandError(f"🔥 Model loading failed: {e}")

        for ticker in tickers:
            self.stdout.write(f"🔄 Processing {ticker}...")

            try:
                df = fetch_data(ticker)
                X, y, scaler = preprocess(df)
                preds = model.predict(X)

                next_price = scaler.inverse_transform(preds)[-1][0]
                y_true = scaler.inverse_transform(y)
                y_pred = scaler.inverse_transform(preds)

                mse = np.mean((y_true - y_pred) ** 2)
                rmse = np.sqrt(mse)
                r2 = 1 - (np.sum((y_true - y_pred)**2) / np.sum((y_true - y_true.mean())**2))

                os.makedirs("media", exist_ok=True)
                plot1 = f"media/{uuid.uuid4()}_history.png"
                plot2 = f"media/{uuid.uuid4()}_compare.png"
                plot_history(df, plot1)
                plot_prediction(y_true, y_pred, plot2)

                # Use any available user or fallback
                user = User.objects.first()
                if not user:
                    raise CommandError("No users found in DB to associate prediction.")

                Prediction.objects.create(
                    user=user,
                    ticker=ticker,
                    next_day_price=next_price,
                    metrics={"mse": mse, "rmse": rmse, "r2": r2},
                    plot1_url=plot1,
                    plot2_url=plot2
                )

                self.stdout.write(self.style.SUCCESS(f"✅ {ticker} predicted successfully. Next-day price: ₹{next_price:.2f}"))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Failed for {ticker}: {e}"))
