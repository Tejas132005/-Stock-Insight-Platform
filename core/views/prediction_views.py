from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.serializers import PredictRequestSerializer, PredictionSerializer
from core.predictions.utils import fetch_data, preprocess
from core.predictions.model_loader import get_model
from core.predictions.plotter import plot_history, plot_prediction
from core.models import Prediction, UserProfile
import os, uuid
import numpy as np
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from rest_framework import generics, filters
from django.conf import settings


class PredictAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        profile = user.userprofile

        today = now().date()
        todays_count = Prediction.objects.filter(user=user, created_at__date=today).count()
        if profile.tier == "free" and todays_count >= 5:
            return Response(
                {"error": "Free tier limit reached. Please upgrade to pro"},
                status=429
            )

        serializer = PredictRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticker = serializer.validated_data['ticker']

        df = fetch_data(ticker)
        X, y, scaler = preprocess(df)
        model = get_model()
        preds = model.predict(X)

        next_price = scaler.inverse_transform(preds)[-1][0]
        y_true = scaler.inverse_transform(y)
        y_pred = scaler.inverse_transform(preds)

        # Metrics
        mse = np.mean((y_true - y_pred) ** 2)
        rmse = np.sqrt(mse)
        r2 = 1 - (np.sum((y_true - y_pred)**2) / np.sum((y_true - y_true.mean())**2))

        # Save plots
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        filename1 = f"{uuid.uuid4()}_history.png"
        filename2 = f"{uuid.uuid4()}_compare.png"
        plot1_path = os.path.join(settings.MEDIA_ROOT, filename1)
        plot2_path = os.path.join(settings.MEDIA_ROOT, filename2)
        plot_history(df, plot1_path)
        plot_prediction(y_true, y_pred, plot2_path)

        # Save to DB
        prediction = Prediction.objects.create(
            user=user,
            ticker=ticker.upper(),
            next_day_price=next_price,
            metrics={"mse": mse, "rmse": rmse, "r2": r2},
            plot1_url=filename1,
            plot2_url=filename2,
        )
        print("..........Images Generated..................")
        print("Plot1 saved to:", plot1_path, "Exists?", os.path.exists(plot1_path))

        return Response(PredictionSerializer(prediction).data)


@login_required
def dashboard(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    predictions = Prediction.objects.filter(user=user).order_by('-created_at')
    return render(request, "dashboard.html", {
        "predictions": predictions,
        "profile": profile
    })
