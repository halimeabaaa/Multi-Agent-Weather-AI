from django.urls import path
from .views import save_health

urlpatterns = [
    path('save/', save_health),
]