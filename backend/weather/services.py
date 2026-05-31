# backend/weather/services.py
import os
from datetime import datetime
from collections import defaultdict

import requests
from django.core.cache import cache


AQI_STATUS_MAP = {
    1: "Çok İyi",
    2: "İyi",
    3: "Orta",
    4: "Kötü",
    5: "Çok Kötü",
}


def _build_cache_key(city_name=None, lat=None, lon=None):
    if lat is not None and lon is not None:
        return f"weather_coords_{round(float(lat), 3)}_{round(float(lon), 3)}"
    if city_name:
        return f"weather_city_{city_name.lower().strip()}"
    return None


def _safe_get_json(url):
    response = requests.get(url, timeout=12)
    if response.status_code != 200:
        return None
    return response.json()


def _fetch_aqi(api_key, lat, lon):
    url = (
        "https://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={lat}&lon={lon}&appid={api_key}"
    )
    data = _safe_get_json(url)
    if not data or not data.get("list"):
        return {"aqi_value": None, "aqi_status": None}

    aqi_raw = data["list"][0]["main"]["aqi"]
    return {
        "aqi_value": aqi_raw,
        "aqi_status": AQI_STATUS_MAP.get(aqi_raw),
    }


def _fetch_uv_index(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=uv_index"
    )
    data = _safe_get_json(url)
    current = (data or {}).get("current", {})
    return current.get("uv_index")


def _fetch_forecast(api_key, lat, lon):
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=tr"
    )
    data = _safe_get_json(url)
    if not data or not data.get("list"):
        return []

    daily = defaultdict(lambda: {"min": None, "max": None, "icon": "cloud"})
    
    # 🎯 [MİMARİ DÜZELTME]: 'Bugün' verisini de listeye katabilmek için katı tarihi kaldırıyoruz.
    # OpenWeather 3 saatlik paketler halinde bugünün kalan saatlerini de döner.
    for item in data["list"]:
        dt_txt = item.get("dt_txt")
        if not dt_txt:
            continue
        
        # Sadece tarihi (YYYY-MM-DD) alarak güne göre gruplama yapıyoruz
        day_str = dt_txt.split(" ")[0]
        temp_min = item["main"]["temp_min"]
        temp_max = item["main"]["temp_max"]

        if daily[day_str]["min"] is None or temp_min < daily[day_str]["min"]:
            daily[day_str]["min"] = temp_min
        if daily[day_str]["max"] is None or temp_max > daily[day_str]["max"]:
            daily[day_str]["max"] = temp_max

        main_condition = item["weather"][0]["main"].lower()
        if "rain" in main_condition:
            daily[day_str]["icon"] = "cloud-showers-heavy"
        elif "clear" in main_condition:
            daily[day_str]["icon"] = "sun"
        elif "snow" in main_condition:
            daily[day_str]["icon"] = "snowflake"
        else:
            daily[day_str]["icon"] = "cloud"

    forecast = []
    days_selections = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    
    # Sistem saatine göre bugünün tarihini güvenle buluyoruz
    today_date = datetime.now().date()

    # Sıralı gün eşleşmesi
    for idx, (day, values) in enumerate(sorted(daily.items())):
        # OpenWeather ücretsiz API'si maksimum 5-6 benzersiz gün dönebilir, taşmayı engelliyoruz
        if idx >= 6:
            break
            
        day_date = datetime.strptime(day, "%Y-%m-%d").date()
        
        # Gün adını Türkçe karşılığına eşliyoruz
        day_name_tr = days_selections[day_date.weekday()]
        
        # Eğer döngüdeki gün bugün ise ismini 'Bugün' olarak revize ediyoruz 🎯
        if day_date == today_date:
            day_name_tr = "Bugün"

        forecast.append(
            {
                "day": day_name_tr,                     # Örn: "Bugün", "Cumartesi"
                "day_tr": day_date.strftime("%d %b"),   # Örn: "29 May"
                "min": round(values["min"]) if values["min"] is not None else None,
                "max": round(values["max"]) if values["max"] is not None else None,
                "icon": values["icon"],
            }
        )
    return forecast


def _icon_for_condition(main_condition):
    main = (main_condition or "").lower()
    if "rain" in main or "drizzle" in main:
        return "cloud-rain"
    if "thunder" in main:
        return "cloud-bolt"
    if "snow" in main:
        return "snowflake"
    if "clear" in main:
        return "sun"
    return "cloud"


def _fetch_hourly(api_key, lat, lon, limit=12):
    """OpenWeather 3 saatlik paketlerden önümüzdeki saatleri döner."""
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=tr"
    )
    data = _safe_get_json(url)
    if not data or not data.get("list"):
        return []

    now = datetime.now()
    hourly = []
    for item in data["list"]:
        dt_txt = item.get("dt_txt")
        if not dt_txt:
            continue
        dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
        if dt < now:
            continue

        main_cond = item["weather"][0]["main"]
        pop = item.get("pop", 0) or 0
        hourly.append({
            "time": dt.strftime("%H:%M"),
            "temp": round(item["main"]["temp"]),
            "condition": item["weather"][0]["description"],
            "main": main_cond,
            "pop_percent": round(float(pop) * 100),
            "icon": _icon_for_condition(main_cond),
        })
        if len(hourly) >= limit:
            break
    return hourly


def _build_weather_alerts(hourly):
    """İlerleyen saatlerde yağış/fırtına varsa tedbir uyarıları üretir."""
    if not hourly:
        return []

    alerts = []
    rain_slots = [
        h for h in hourly
        if "rain" in h["main"].lower()
        or "drizzle" in h["main"].lower()
        or h["pop_percent"] >= 55
    ]
    storm_slots = [h for h in hourly if "thunder" in h["main"].lower()]
    snow_slots = [h for h in hourly if "snow" in h["main"].lower()]

    if rain_slots:
        hours_txt = ", ".join(h["time"] for h in rain_slots[:4])
        alerts.append({
            "type": "rain",
            "severity": "yüksek" if any(h["pop_percent"] >= 75 for h in rain_slots) else "orta",
            "title": "Yaklaşan yağış",
            "message": (
                f"Önümüzdeki saatlerde yağış bekleniyor ({hours_txt}). "
                "Şemsiye ve su geçirmez giysi bulundurun; açık hava etkinliklerinizi yeniden planlayın."
            ),
            "hours": [h["time"] for h in rain_slots],
        })
    if storm_slots:
        alerts.append({
            "type": "storm",
            "severity": "yüksek",
            "title": "Fırtına riski",
            "message": "Gök gürültülü fırtına ihtimali var. Açık alanda kalmayın, güvenli kapalı alana geçin.",
            "hours": [h["time"] for h in storm_slots],
        })
    if snow_slots:
        alerts.append({
            "type": "snow",
            "severity": "orta",
            "title": "Kar yağışı",
            "message": "Kar yağışı bekleniyor. Kaygan zemin ve düşük görüşe karşı tedbirli olun.",
            "hours": [h["time"] for h in snow_slots],
        })
    return alerts


def search_cities(query, limit=8):
    """OpenWeather geocoding ile şehir arar (Türkçe/İngilizce isim)."""
    q = (query or "").strip()
    if len(q) < 2:
        return []

    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return []

    url = (
        "https://api.openweathermap.org/geo/1.0/direct"
        f"?q={requests.utils.quote(q)}&limit={limit}&appid={api_key}"
    )
    data = _safe_get_json(url)
    if not data:
        return []

    results = []
    for item in data:
        name = item.get("name", "")
        state = item.get("state")
        country = item.get("country", "")
        label = name
        if state:
            label = f"{name}, {state}"
        if country:
            label = f"{label} ({country})"
        results.append({
            "label": label,
            "name": name,
            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "country": country,
        })
    return results


def get_weather_data(city_name=None, lat=None, lon=None):
    cache_key = _build_cache_key(city_name=city_name, lat=lat, lon=lon)
    if not cache_key:
        return {"success": False, "message": "Şehir adı veya koordinat zorunlu."}

    cached_weather = cache.get(cache_key)
    if cached_weather:
        return cached_weather

    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return {"success": False, "message": "WEATHER_API_KEY tanımlı değil."}

    if lat is not None and lon is not None:
        current_url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=tr"
        )
    else:
        current_url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city_name}&appid={api_key}&units=metric&lang=tr"
        )

    current = _safe_get_json(current_url)
    if not current:
        return {"success": False, "message": "Anlık hava verisi alınamadı."}

    coord = current.get("coord") or {}
    resolved_lat = coord.get("lat")
    resolved_lon = coord.get("lon")
    if resolved_lat is None or resolved_lon is None:
        return {"success": False, "message": "Konum koordinatları çözümlenemedi."}

    aqi_data = _fetch_aqi(api_key, resolved_lat, resolved_lon)
    uv_index = _fetch_uv_index(resolved_lat, resolved_lon)
    forecast = _fetch_forecast(api_key, resolved_lat, resolved_lon)
    hourly = _fetch_hourly(api_key, resolved_lat, resolved_lon)
    weather_alerts = _build_weather_alerts(hourly)

    weather_info = {
        "success": True,
        "city": current.get("name"),
        "lat": resolved_lat,
        "lon": resolved_lon,
        "temp": current["main"]["temp"],
        "feels_like": current["main"]["feels_like"],
        "humidity": current["main"]["humidity"],
        "condition": current["weather"][0]["description"],
        "main_condition": current["weather"][0]["main"],
        "uv_index": uv_index,
        "aqi_value": aqi_data["aqi_value"],
        "aqi_status": aqi_data["aqi_status"],
        "forecast": forecast,
        "hourly": hourly,
        "weather_alerts": weather_alerts,
    }

    # Kullanıcı ekranı için 5 dakikalık cache süresi
    cache.set(cache_key, weather_info, timeout=300)
    return weather_info