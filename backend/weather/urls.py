from django.urls import path
from .views import save_location, current_weather, geocode_city_search

urlpatterns = [
    path('save-location/', save_location, name='save_location'),
    path('current/', current_weather, name='current_weather'),
    path('search/', geocode_city_search, name='geocode_city_search'),
]