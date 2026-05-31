# summary/services.py
import os
from django.utils import timezone

import httpx
from django.conf import settings
from common.datetime_tr import format_tr_date, format_tr_time, local_now
from health.models import UserHealth
from profiles.health_context import build_health_profile_dict
# 🎯 [YENİ]: Takvim etkinliklerini çekebilmek için takvim modelini içeri alıyoruz


def _build_profile_payload(profile, user):
    base = build_health_profile_dict(user, profile)
    return {
        "min_temp": base["min_temp"],
        "max_temp": base["max_temp"],
        "favorite_weather": base["favorite_weather"],
        "disliked_weather": base["disliked_weather"],
        "activities": base["activities"],
        "blood_type": base["blood_type"],
        "medications": base["medications"],
        "allergies": base["allergies"],
        "health_notes": base["health_notes"],
    }


def _build_health_payload(user):
    health_records = (
        UserHealth.objects.filter(user=user)
        .select_related("condition")
        .order_by("condition__name")
    )
    lines = [
        f"{record.condition.name} (şiddet: {record.severity})"
        for record in health_records
    ]
    ctx = build_health_profile_dict(user)
    if ctx["blood_type"]:
        lines.append(f"Kan grubu: {ctx['blood_type']}")
    for med in ctx["medications"]:
        lines.append(f"İlaç: {med}")
    for allergy in ctx["allergies"]:
        lines.append(f"Alerji: {allergy}")
    if ctx["health_notes"]:
        lines.append(f"Not: {ctx['health_notes']}")
    return lines


# summary/services.py içindeki ilgili fonksiyon güncellemesi:

def _build_calendar_payload(user):
    """Yaklaşan etkinlikleri tam tarih/saat ile listeler (AI tarih karıştırmasın diye)."""
    from calendar_app.models import CalendarEvent

    now = local_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = today_start + timezone.timedelta(days=7)

    events = CalendarEvent.objects.filter(
        user=user,
        start_datetime__lt=window_end,
        end_datetime__gte=now,
    ).order_by("start_datetime")

    events_list = []
    tomorrow = today_start + timezone.timedelta(days=1)

    for ev in events:
        start_local = timezone.localtime(ev.start_datetime)
        end_local = timezone.localtime(ev.end_datetime)
        date_label = format_tr_date(start_local)
        iso_date = start_local.strftime("%Y-%m-%d")
        time_str = format_tr_time(start_local)
        if end_local.date() == start_local.date():
            end_time = format_tr_time(end_local)
            if end_time != time_str:
                time_str = f"{time_str}-{end_time}"

        if start_local.date() == now.date():
            relative = "bugün"
        elif start_local.date() == tomorrow.date():
            relative = "yarın"
        else:
            relative = "yaklaşan"

        location_str = f" | Yer: {ev.location}" if ev.location else ""

        events_list.append(
            f"Tarih: {iso_date} ({date_label}, {relative}) | Saat: {time_str} | "
            f"Başlık: {ev.title} | Açıklama: {ev.description or 'Yok'}{location_str}"
        )

    return events_list

def generate_ai_summary(user, profile, weather_info):
    ai_url = os.getenv("AI_SUMMARY_URL", settings.AI_SUMMARY_URL)
    
    # 🎯 Takvim verilerini topluyoruz
    calendar_events = _build_calendar_payload(user)
    
    payload = {
        "user_id": user.id,
        "username": user.username,
        "profile": _build_profile_payload(profile, user),
        "health": _build_health_payload(user),
        "calendar_events": calendar_events,
        "weather": {
            "temp": weather_info["temp"],
            "condition": weather_info["condition"],
            "aqi_value": weather_info.get("aqi_value"),
            "aqi_status": weather_info.get("aqi_status"),
            "uv_index": weather_info.get("uv_index"),
            "hourly": weather_info.get("hourly", []),
            "weather_alerts": weather_info.get("weather_alerts", []),
        },
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(ai_url, json=payload)
    except Exception as exc:
        return _fallback_summary(user, profile, weather_info, calendar_events, f"Servis hatası: {exc}")

    if response.status_code != 200:
        return _fallback_summary(
            user,
            profile,
            weather_info,
            calendar_events,
            f"HTTP {response.status_code}",
        )

    data = response.json()
    summary = data.get("summary")
    if not summary:
        return _fallback_summary(user, profile, weather_info, calendar_events, "Boş özet")

    return {
        "success": True,
        "summary": summary,
        "risk": data.get("risk"),
    }


def _fallback_summary(user, profile, weather_info, calendar_events, reason):
    """
    AI servisi çökerse bile kullanıcıya takvim etkinliklerini de hatırlatan 
    kurşun geçirmez insani fallback algoritması.
    """
    temp = weather_info.get("temp")
    condition = weather_info.get("condition")
    city = weather_info.get("city") or "bulunduğun yerde"

    min_temp = profile.min_temp
    max_temp = profile.max_temp
    if min_temp is not None and max_temp is not None and min_temp > max_temp:
        min_temp, max_temp = max_temp, min_temp

    disliked = [s.lower() for s in profile.disliked_weather or []]
    favorite = [s.lower() for s in profile.favorite_weather or []]

    hot = temp is not None and temp >= 35
    cold = temp is not None and temp <= 5

    range_severity = "unknown"
    if temp is not None and min_temp is not None and max_temp is not None:
        if min_temp <= temp <= max_temp:
            range_severity = "inside"
        else:
            distance = min(abs(temp - min_temp), abs(temp - max_temp))
            range_severity = "outside_hard" if distance >= 8 else "outside_soft"

    # 🎯 [YENİ]: Fallback metnine takvim verilerini eklemek için şablon oluşturuyoruz
    calendar_note = ""
    if calendar_events:
        event_count = len(calendar_events)
        titles_preview = "; ".join(
            e.split("Başlık: ")[1].split(".")[0] if "Başlık: " in e else e[:40]
            for e in calendar_events[:5]
        )
        calendar_note = (
            f" Takviminde önümüzdeki günlerde {event_count} etkinlik planlı"
            f" ({titles_preview}). Her birini hava durumuna göre ayrı ayrı değerlendir."
        )

    if range_severity == "outside_hard":
        if temp > max_temp:
            text = (
                f"Sevgili {user.username}, bugün {city} senin tercih aralığının [{int(min_temp)},{int(max_temp)}]°C "
                f"çok üstünde ve gerçekten bunaltıcı ({int(temp)}°C, {condition}). "
                f"Bugün açık alanda uzun kalma; serin, gölgeli veya klimalı alanlarda kalmaya özen göster. "
                f"Dışarı çıkacaksan şapka, su ve hafif kıyafet şart.{calendar_note}"
            )
        else:
            text = (
                f"Sevgili {user.username}, bugün {city} sıcaklığı senin tercih aralığının [{int(min_temp)},{int(max_temp)}]°C "
                f"çok altında ({int(temp)}°C, {condition}). "
                f"Dışarıda uzun süre kalmaktansa sıcak ve korunaklı ortamlarda bulunman daha iyi olur. "
                f"Katmanlı giyinmeyi ve vücut sıcaklığını korumayı ihmal etme.{calendar_note}"
            )
        risk = "high"
    elif range_severity == "inside":
        preferred_activity = (profile.activities or ["kısa yürüyüş"])[0]
        text = (
            f"Harika haber {user.username}! Bugün {city} için sıcaklık {int(temp)}°C ve "
            f"senin tercih aralığın [{int(min_temp)},{int(max_temp)}]°C içinde. "
            f"Hava gerçekten sana uygun görünüyor; {preferred_activity} gibi sevdiğin bir aktiviteyi "
            f"rahatça planlayabilirsin.{calendar_note}"
        )
        risk = "low"
    elif hot or any("sıcak" in d for d in disliked):
        text = (
            f"Sevgili {user.username}, bugün {city} için gerçekten berbat derecede sıcak bir hava var "
            f"({int(temp)}°C civarı, {condition}). Mümkün olduğunca serin ve gölgeli ortamlarda kalmaya, "
            f"çok su içmeye ve dışarı çıkman gerekiyorsa şapka gibi koruyucu önlemler almaya özen göster. "
            f"Ağır egzersizleri serin saatlere bırakmak iyi bir fikir olabilir.{calendar_note}"
        )
        risk = "high"
    elif any("yağmur" in f or "rain" in f for f in favorite) and "yağmur" in (condition or "").lower():
        text = (
            f"Bugün {city} için hava tam sana göre: {condition}, sıcaklık yaklaşık {int(temp)}°C. "
            f"Ben senin yerinde olsam hafif bir yağmur koşusuna çıkar, temiz havanın tadını çıkarırdım. "
            f"Yine de üşütmemek için eve döndüğünde kuru kıyafetlere geçmeyi unutma.{calendar_note}"
        )
        risk = "low"
    elif cold:
        text = (
            f"{city} genelinde hava oldukça soğuk ({int(temp)}°C civarı, {condition}). "
            f"Eğer dışarı çıkman gerekiyorsa katmanlı ve sıcak giyinmek, özellikle de baş ve elleri korumak çok önemli. "
            f"Sıcak içecekler ve hafif hareketlerle vücudu ısıtmak sana iyi gelecektir.{calendar_note}"
        )
        risk = "medium"
    else:
        comfort_note = ""
        if min_temp is not None and max_temp is not None and temp is not None:
            if temp < min_temp:
                comfort_note = " Senin tercih aralığının biraz altında; serin bir gün."
            elif temp > max_temp:
                comfort_note = " Senin tercih aralığının üstünde; rahatsız hissettirebilir."
            else:
                comfort_note = " Sıcaklık tercih aralığında."

        text = (
            f"Merhaba {user.username}, bugün {city} için hava {condition} ve sıcaklık yaklaşık {int(temp)}°C."
            f"{comfort_note} Güne uygun, seni iyi hissettirecek küçük bir yürüyüş veya sevdiğin bir aktivite "
            f"gününe güzel gelebilir.{calendar_note}"
        )
        risk = "low"

    return {
        "success": True,
        "summary": text,
        "risk": risk,
        "fallback_reason": reason,
    }