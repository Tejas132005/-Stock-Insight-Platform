from django.contrib import admin
from core.models import Prediction

@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ticker', 'next_day_price', 'created_at')
    search_fields = ('ticker', 'user__username')
