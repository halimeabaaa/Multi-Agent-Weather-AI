# backend/ai_orchestrator/tasks.py
import httpx
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import DailySummary

User = get_user_model()

FASTAPI_URL = "http://127.0.0.1:8005/api/v1/generate-summary"

@shared_task
def generate_daily_summary_task():
    users = User.objects.all()
    today = timezone.now().date()
    
    for user in users:
        try:
            user_profile = {
                "favorite_weather": ["rain"]
            }
            health_data = ["Alerjik Rinit"] 
            
            weather_data = {
                "temp": 18,
                "pollen": "Yüksek",
                "condition": "Parçalı Bulutlu"
            }
            
            payload = {
                "user_id": user.id,
                "profile": user_profile,
                "health": health_data,
                "weather": weather_data
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(FASTAPI_URL, json=payload)
                
                if response.status_code == 200:
                    ai_result = response.json()
                    
                    # 🔥 ORM'İ BYPASS EDEN GÜVENLİ MANUEL KONTROL:
                    # update_or_create kullanmıyoruz, önce kaydın varlığını filtreliyoruz
                    summary_queryset = DailySummary.objects.filter(user_id=user.id, date=today)
                    
                    if summary_queryset.exists():
                        # Kayıt varsa güncelle
                        summary_queryset.update(
                            risk_level=ai_result.get("risk", "low"),
                            summary_text=ai_result.get("summary", "")
                        )
                    else:
                        # Kayıt yoksa tertemiz yeni oluştur
                        DailySummary.objects.create(
                            user_id=user.id,
                            date=today,
                            risk_level=ai_result.get("risk", "low"),
                            summary_text=ai_result.get("summary", "")
                        )
                        
                    print(f"✅ {user.username} için günlük AI özeti başarıyla oluşturuldu ve kaydedildi.")
                else:
                    print(f"❌ {user.username} için FastAPI hatası: {response.status_code}")
                    
        except Exception as e:
            print(f"💥 {user.username} özeti üretilirken hata oluştu: {str(e)}")