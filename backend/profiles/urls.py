from django.urls import path
from .views import save_onboarding, get_my_profile # 🎯 Yeni fonksiyonu ekledik

urlpatterns = [
    path('save/', save_onboarding, name='save_onboarding'),
    path('me/', get_my_profile, name='get_my_profile'), # 🎯 Frontend'in sorgu atacağı me/ endpoint'i
]