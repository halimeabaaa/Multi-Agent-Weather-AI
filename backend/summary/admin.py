# summary/admin.py
from django.contrib import admin
from .models import DailySummary

@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin): # 👈 Doğru olan 'admin.ModelAdmin' olarak düzeltildi
    list_display = ('user', 'city', 'temp', 'weather_type', 'risk_level', 'created_at')
    list_filter = ('risk_level', 'city', 'created_at')
    search_fields = ('user__username', 'summary')