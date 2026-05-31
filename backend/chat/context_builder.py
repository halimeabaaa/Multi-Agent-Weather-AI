"""Sohbet botu için kullanıcının tüm bağlam verisini toplar."""
from common.datetime_tr import build_reference_datetime_context
from profiles.health_context import build_health_profile_dict
from profiles.models import UserProfile
from summary.services import _build_calendar_payload
from weather.models import UserLocation
from weather.services import get_weather_data


def build_chat_context(user):
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None

    health = build_health_profile_dict(user, profile)
    calendar_events = _build_calendar_payload(user)

    weather_data = {
        "temp": None,
        "condition": "bilinmiyor",
        "pollen": "Veri Yok",
        "aqi_value": None,
        "aqi_status": None,
        "uv_index": None,
        "hourly": [],
        "weather_alerts": [],
    }

    try:
        location = UserLocation.objects.get(user=user)
        api = get_weather_data(lat=location.lat, lon=location.lon)
    except UserLocation.DoesNotExist:
        api = get_weather_data(city_name="Istanbul")

    if api and api.get("success"):
        weather_data = {
            "temp": api.get("temp"),
            "condition": api.get("condition"),
            "pollen": api.get("pollen") or "Veri Yok",
            "aqi_value": api.get("aqi_value"),
            "aqi_status": api.get("aqi_status"),
            "uv_index": api.get("uv_index"),
            "hourly": api.get("hourly", []),
            "weather_alerts": api.get("weather_alerts", []),
            "city": api.get("city"),
        }

    user_profile = {
        "username": f"{user.first_name} {user.last_name}".strip() or user.username,
        "email": user.email or "",
        **health,
    }

    return {
        "user_profile": user_profile,
        "weather_data": weather_data,
        "calendar_events": calendar_events,
        "reference_datetime": build_reference_datetime_context(),
    }
