# backend/summary/tasks.py
import os

import httpx
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from health.models import UserHealth
from weather.models import UserLocation
from weather.services import get_weather_data
from .models import DailySummary

User = get_user_model()

FASTAPI_URL = os.getenv("AI_SUMMARY_URL", "http://fastapi:8005/api/v1/generate-summary")

@shared_task
def generate_all_users_daily_summary():
    users = User.objects.filter(is_active=True)
    success_count = 0
    today = timezone.now().date()
    
    for user in users:
        if DailySummary.objects.filter(user=user, created_at__date=today).exists():
            continue

        location = UserLocation.objects.filter(user=user).first()
        if not location: 
            continue
            
        weather_info = get_weather_data(lat=location.lat, lon=location.lon)
        if not weather_info or not weather_info.get("success"): 
            continue
            
        health_list = list(
            UserHealth.objects.filter(user=user)
            .select_related("condition")
            .values_list("condition__name", flat=True)
        )

        try:
            profile = user.userprofile
            user_profile_dict = {
                "min_temp": profile.min_temp,
                "max_temp": profile.max_temp,
                "favorite_weather": profile.favorite_weather,
                "disliked_weather": profile.disliked_weather,
                "activities": profile.activities,
            }
        except AttributeError:
            continue

        payload = {
            "user_id": user.id,
            "profile": user_profile_dict,
            "health": health_list,
            "weather": {
                "temp": weather_info.get("temp"),
                "condition": weather_info.get("condition"),
                "city": weather_info.get("city"),
                "uv_index": weather_info.get("uv_index"),
                "aqi_value": weather_info.get("aqi_value"),
                "aqi_status": weather_info.get("aqi_status"),
            },
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(FASTAPI_URL, json=payload)
                
                if response.status_code == 200:
                    ai_result = response.json()

                    summary_text = ai_result.get("summary")
                    if not summary_text:
                        continue

                    DailySummary.objects.create(
                        user=user,
                        city=weather_info.get("city", location.city or "Bilinmiyor"),
                        temp=weather_info.get("temp") or 0,
                        weather_type=weather_info.get("main_condition") or weather_info.get("condition") or "Unknown",
                        pollen="Bilinmiyor",
                        risk_level=(ai_result.get("risk") or "orta").capitalize(),
                        summary=summary_text,
                    )
                    success_count += 1
                else:
                    print(f"❌ {user.username} için FastAPI hatası: {response.status_code}")
                    
        except Exception as e:
            print(f"💥 {user.username} AI özeti üretilirken hata oluştu: {str(e)}")
            continue
            
    return f"Büyük AI Otomasyonu tamamlandı. {success_count} kullanıcı işlendi."