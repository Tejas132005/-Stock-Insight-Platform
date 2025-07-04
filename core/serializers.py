from rest_framework import serializers
from .models import Prediction

class PredictRequestSerializer(serializers.Serializer):
    ticker = serializers.CharField(max_length=10)

class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = '__all__'
