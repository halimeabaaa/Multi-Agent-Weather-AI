# summary/views.py
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from django.db.models import Count

from weather.services import get_weather_data
from profiles.models import UserProfile
from profiles.health_context import build_health_profile_dict, get_user_condition_names
from health.models import HealthCondition
from .models import DailySummary, SystemLog, SystemNotification
from .services import generate_ai_summary

TR_WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

FILTER_TYPE_LABELS = {
    "all": "Herkese",
    "disease": "Sağlık hassasiyeti",
    "city": "Şehir",
    "user": "Tek kullanıcı",
}

NOTIFICATION_DISPLAY_HEADING = "Kullanıcılarımızın Dikkatine"

ALLOWED_DURATION_HOURS = {6, 12, 24, 72, 168, 720}


def _serialize_notification(n):
    now = timezone.now()
    expires_at = getattr(n, "expires_at", None) or (n.created_at + timedelta(days=7))
    remaining = expires_at - now
    if remaining.total_seconds() <= 0:
        remaining_label = "Süresi doldu"
    elif remaining.days >= 1:
        remaining_label = f"{remaining.days} gün kaldı"
    elif remaining.seconds >= 3600:
        remaining_label = f"{int(remaining.total_seconds() // 3600)} saat kaldı"
    else:
        remaining_label = f"{max(1, int(remaining.total_seconds() // 60))} dk kaldı"

    return {
        "id": n.id,
        "heading": NOTIFICATION_DISPLAY_HEADING,
        "title": n.title,
        "message": n.message,
        "type": n.filter_type,
        "date": n.created_at.strftime("%d.%m.%Y %H:%M"),
        "expires_at": expires_at.strftime("%d.%m.%Y %H:%M"),
        "remaining_label": remaining_label,
        "is_expired": expires_at <= now,
    }


def _user_disease_names(user):
    return get_user_condition_names(user)


def _active_notifications_qs():
    qs = SystemNotification.objects.filter(is_active=True)
    try:
        return qs.filter(expires_at__gt=timezone.now())
    except Exception:
        return qs


def _user_last_city(user):
    city = (
        DailySummary.objects.filter(user=user)
        .order_by("-created_at")
        .values_list("city", flat=True)
        .first()
    )
    return city or "Henüz rapor yok"


def _user_activities_label(profile):
    if not profile or not profile.activities:
        return "Belirtilmemiş"
    items = [str(a).strip() for a in profile.activities if a]
    return ", ".join(items) if items else "Belirtilmemiş"


def _pack_weather_metrics(weather_info):
    return {
        "temperature": round(weather_info["temp"]),
        "feels_like": round(weather_info["feels_like"]),
        "detail_condition": weather_info["condition"],
        "uv_index": weather_info.get("uv_index"),
        "aqi_value": weather_info.get("aqi_value"),
        "aqi_status": weather_info.get("aqi_status"),
        "hourly": weather_info.get("hourly", []),
        "weather_alerts": weather_info.get("weather_alerts", []),
    }


def _count_by_last_7_days(queryset, date_field="created_at"):
    today = timezone.localdate()
    labels = []
    counts = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        labels.append(TR_WEEKDAYS[day.weekday()])
        counts.append(queryset.filter(**{f"{date_field}__date": day}).count())
    return labels, counts


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_daily_summary(request):
    user = request.user
    
    # 1. Kullanıcı profilini güvenle çekiyoruz
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return Response(
            {"success": False, "message": "Önce profil kurulumunu tamamlamalısınız."},
            status=status.HTTP_404_NOT_FOUND
        )

    # 2. URL'den gelen koordinat parametrelerini yakalıyoruz
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")
    city_name = request.query_params.get("city")

    # 3. Hava durumu verisini çekiyoruz
    if lat and lon:
        weather_info = get_weather_data(lat=lat, lon=lon)
    elif city_name:
        weather_info = get_weather_data(city_name=city_name)
    else:
        weather_info = get_weather_data(city_name="Malatya")

    if not weather_info or not weather_info.get("success"):
        return Response(
            {"success": False, "message": weather_info.get("message", "Hava durumu hatası.")},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 4. Bugün üretilmiş bir özet var mı kontrolü
    today = timezone.now().date()
    resolved_city = weather_info.get("city", "Bilinmeyen Şehir")
    
    force_refresh = request.query_params.get("refresh") == "1"

    summary_obj = None
    if not force_refresh:
        summary_obj = DailySummary.objects.filter(
            user=user,
            created_at__date=today,
            city=resolved_city,
        ).first()

    if summary_obj:
        response_data = {
            "user": {
                "username": user.username, 
                "city": resolved_city,
                "is_staff": user.is_staff
            },
            "weather_metrics": _pack_weather_metrics(weather_info),
            "ai_advisory": {
                "summary_card": summary_obj.summary,
                "risk_level": summary_obj.risk_level,
            },
            "forecast": weather_info.get("forecast", []),
        }
        
        try:
            SystemLog.objects.create(
                user=user,
                action="Hava Durumu İnceleme",
                details=f"{resolved_city} şehri için mevcut özet görüntülendi. Sıcaklık: {weather_info['temp']}°C",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass
            
        return Response(response_data, status=status.HTTP_200_OK)

    # 5. Eğer bugün için özet yoksa yeni AI özeti üretiyoruz
    ai_result = generate_ai_summary(user, profile, weather_info)
    
    if ai_result.get("success"):
        summary_text = ai_result["summary"]
        risk_lvl = ai_result.get("risk", "Orta")
        
        DailySummary.objects.create(
            user=user,
            city=resolved_city,
            temp=round(weather_info["temp"]),
            weather_type=weather_info["main_condition"],
            risk_level=risk_lvl,
            summary=summary_text
        )
    else:
        summary_text = "AI servisi şu an meşgul, lütfen daha sonra tekrar deneyiniz."
        risk_lvl = "Orta"

    # 6. Başarılı veriyi paketleyip dönüyoruz
    response_data = {
        "user": {
            "username": user.username, 
            "city": resolved_city,
            "is_staff": user.is_staff
        },
        "weather_metrics": _pack_weather_metrics(weather_info),
        "ai_advisory": {
            "summary_card": summary_text,
            "risk_level": risk_lvl,
        },
        "forecast": weather_info.get("forecast", []),
    }

    try:
        SystemLog.objects.create(
            user=user,
            action="AI Özet Tetiklendi",
            details=f"{resolved_city} şehri için yeni bağlamsal analiz ve yapay zeka raporu üretildi.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
    except Exception:
        pass

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_summary_history(request):
    user = request.user
    histories = DailySummary.objects.filter(user=user).order_by("-created_at")
    
    history_data = []
    for h in histories:
        history_data.append({
            "id": h.id,
            "city": h.city,
            "temp": h.temp,
            "weather_type": h.weather_type,
            "risk_level": h.risk_level,
            "summary": h.summary,
            "date": h.created_at.strftime("%Y-%m-%d"),
            "time": h.created_at.strftime("%H:%M")
        })
        
    return Response({"success": True, "history": history_data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard_stats(request):
    """Yönetim paneli: metrikler, kullanıcılar, loglar ve grafik verileri (veritabanından)."""
    if not request.user.is_staff:
        return Response({"success": False, "error": "Bu panele erişim yetkiniz yok."}, status=403)

    try:
        return _build_admin_dashboard_response(request)
    except Exception as exc:
        return Response(
            {
                "success": False,
                "error": (
                    "Yönetim verileri okunamadı. Veritabanı göçlerini çalıştırın: "
                    "python manage.py migrate"
                ),
                "detail": str(exc),
            },
            status=500,
        )


def _build_admin_dashboard_response(request):
    User = get_user_model()
    users = User.objects.all().order_by("-id")
    logs = SystemLog.objects.all().select_related("user").order_by("-created_at")[:100]

    last_24h = timezone.now() - timedelta(hours=24)
    active_today = User.objects.filter(last_login__gte=last_24h).count()
    ai_generations_today = SystemLog.objects.filter(
        action="AI Özet Tetiklendi", created_at__gte=last_24h
    ).count()
    fallback_count_today = SystemLog.objects.filter(
        details__icontains="fallback", created_at__gte=last_24h
    ).count()
    summaries_today = DailySummary.objects.filter(created_at__gte=last_24h).count()

    profiles_by_user = {
        p.user_id: p
        for p in UserProfile.objects.select_related("user").all()
    }

    users_list = []
    for u in users:
        profile = profiles_by_user.get(u.id)
        health = build_health_profile_dict(u, profile)
        diseases = health["diseases"]
        users_list.append({
            "id": u.id,
            "username": u.username,
            "email": u.email or "",
            "is_staff": u.is_staff,
            "city": _user_last_city(u),
            "diseases": ", ".join(diseases) if diseases else "Kayıtlı hassasiyet yok",
            "blood_type": health["blood_type"] or "Belirtilmemiş",
            "medications": ", ".join(health["medications"]) if health["medications"] else "Belirtilmemiş",
            "allergies": ", ".join(health["allergies"]) if health["allergies"] else "Belirtilmemiş",
            "health_notes": health["health_notes"] or "—",
            "activities": _user_activities_label(profile),
            "is_onboarded": bool(profile and profile.is_onboarded),
            "date_joined": u.date_joined.strftime("%d.%m.%Y"),
            "last_login": u.last_login.strftime("%d.%m.%Y %H:%M") if u.last_login else "Hiç giriş yok",
        })

    logs_list = [
        {
            "id": log.id,
            "username": log.user.username if log.user_id else "Sistem",
            "action": log.action,
            "details": log.details,
            "date": log.created_at.strftime("%d.%m.%Y %H:%M"),
        }
        for log in logs
    ]

    chart_labels, user_trend = _count_by_last_7_days(User.objects.all(), "date_joined")
    _, ai_trend = _count_by_last_7_days(
        SystemLog.objects.filter(action="AI Özet Tetiklendi"),
        "created_at",
    )

    risk_rows = (
        DailySummary.objects.values("risk_level")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    risk_labels = []
    risk_counts = []
    risk_color_map = {
        "düşük": "#22c55e",
        "orta": "#f59e0b",
        "yüksek": "#ef4444",
    }
    risk_colors = []
    for row in risk_rows:
        level = (row["risk_level"] or "Belirsiz").strip()
        risk_labels.append(level)
        risk_counts.append(row["count"])
        risk_colors.append(
            risk_color_map.get(level.lower(), "#94a3b8")
        )

    action_rows = (
        SystemLog.objects.values("action")
        .annotate(count=Count("id"))
        .order_by("-count")[:1]
    )
    top_feature = (
        action_rows[0]["action"]
        if action_rows
        else "Henüz sistem kaydı yok"
    )

    activity_counts = {}
    for prof in UserProfile.objects.all():
        for act in prof.activities or []:
            name = str(act).strip()
            if name:
                activity_counts[name] = activity_counts.get(name, 0) + 1
    top_cohort = (
        max(activity_counts, key=activity_counts.get)
        if activity_counts
        else "Henüz aktivite verisi yok"
    )

    return Response({
        "success": True,
        "metrics": {
            "total_users": users.count(),
            "active_today": active_today,
            "ai_generations_today": ai_generations_today or summaries_today,
            "fallback_count_today": fallback_count_today,
            "total_logs": SystemLog.objects.count(),
            "total_summaries": DailySummary.objects.count(),
            "total_notifications": _active_notifications_qs().count(),
        },
        "charts": {
            "labels": chart_labels,
            "user_trend": user_trend,
            "ai_trend": ai_trend,
            "risk_labels": risk_labels or ["Veri yok"],
            "risk_counts": risk_counts or [0],
            "risk_colors": risk_colors or ["#94a3b8"],
        },
        "product": {
            "top_feature": top_feature,
            "top_cohort": top_cohort,
        },
        "users": users_list,
        "logs": logs_list,
    }, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_get_unique_filters(request):
    """Bildirim hedefleri: veritabanındaki tekil hastalık, şehir ve kullanıcı listesi."""
    if not request.user.is_staff:
        return Response({"success": False, "error": "Yetkisiz erişim."}, status=403)

    User = get_user_model()

    unique_diseases = sorted(
        HealthCondition.objects.filter(userhealth__isnull=False)
        .values_list("name", flat=True)
        .distinct()
    )
    unique_cities = sorted(
        {
            c.strip()
            for c in DailySummary.objects.exclude(city="")
            .values_list("city", flat=True)
            .distinct()
            if c and c.strip()
        }
    )
    unique_users = [
        {"email": u.email, "username": u.username}
        for u in User.objects.exclude(email="").order_by("username")
    ]

    return Response({
        "success": True,
        "diseases": unique_diseases,
        "cities": unique_cities,
        "users": unique_users,
    }, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_list_notifications(request):
    """Yönetim paneli: yayınlanan tüm sistem bildirimleri."""
    if not request.user.is_staff:
        return Response({"success": False, "error": "Yetkisiz erişim."}, status=403)

    notifications = SystemNotification.objects.all().order_by("-created_at")[:50]
    data_list = []
    for n in notifications:
        item = _serialize_notification(n)
        item["type_label"] = FILTER_TYPE_LABELS.get(n.filter_type, n.filter_type)
        item["filter_value"] = n.filter_value or "—"
        item["is_active"] = n.is_active and not item["is_expired"]
        data_list.append(item)
    return Response({"success": True, "notifications": data_list}, status=200)


# summary/views.py içindeki ilgili alt fonksiyonların düzeltilmiş kurşun geçirmez hali:

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_create_notification(request):
    """
    🔒 [SADECE ADMIN]: İki aşamalı filtre tipine ve seçilen dinamik değere 
    göre akıllı sistem bildirimi oluşturur ve veritabanına işler.
    """
    if not request.user.is_staff:
        return Response({"success": False, "error": "Yetkiniz yok."}, status=403)

    filter_type = request.data.get("filter_type", "all")
    filter_value = request.data.get("filter_value")
    title = request.data.get("title")
    message = request.data.get("message")

    try:
        duration_hours = int(request.data.get("duration_hours", 24))
    except (TypeError, ValueError):
        duration_hours = 24

    if duration_hours not in ALLOWED_DURATION_HOURS:
        return Response(
            {"success": False, "error": "Geçersiz yayın süresi seçildi."},
            status=400,
        )

    if not title or not message:
        return Response(
            {"success": False, "error": "Konu ve uyarı metni doldurulmalıdır."},
            status=400,
        )

    if filter_type != "all" and filter_value:
        filter_value = str(filter_value).strip().lower()
    else:
        filter_value = None

    expires_at = timezone.now() + timedelta(hours=duration_hours)

    notification = SystemNotification.objects.create(
        filter_type=filter_type,
        filter_value=filter_value,
        title=title,
        message=message,
        expires_at=expires_at,
    )

    try:
        SystemLog.objects.create(
            user=request.user,
            action="Bildirim Yayınlandı",
            details=f"Filtre: {filter_type.upper()} ({filter_value or 'Herkes'}) - Başlık: {title}"
        )
    except Exception:
        pass

    return Response({
        "success": True,
        "message": "Duyuru yayınlandı.",
        "notification": _serialize_notification(notification),
    }, status=201)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def admin_delete_notification(request, notification_id):
    """Yönetim paneli: yanlış yayınlanan bildirimi siler."""
    if not request.user.is_staff:
        return Response({"success": False, "error": "Yetkiniz yok."}, status=403)

    deleted, _ = SystemNotification.objects.filter(id=notification_id).delete()
    if not deleted:
        return Response({"success": False, "error": "Bildirim bulunamadı."}, status=404)

    try:
        SystemLog.objects.create(
            user=request.user,
            action="Bildirim Silindi",
            details=f"Bildirim #{notification_id} yönetici tarafından kaldırıldı.",
        )
    except Exception:
        pass

    return Response({"success": True, "message": "Bildirim silindi."}, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_notifications(request):
    """
    🔒 [KULLANICI]: Giriş yapan kullanıcının tüm profil katmanlarını (hastalık, şehir, e-posta)
    büyük-küçük harf duyarsız olarak denetler ve tam nokta atışı süzme yapar.
    """
    user = request.user
    
    user_diseases = [str(d).lower().strip() for d in _user_disease_names(user) if d]
    user_city = _user_last_city(user).lower().strip()
    if user_city == "henüz rapor yok":
        user_city = ""
        
    user_email = str(user.email).lower().strip() if user.email else ""

    now = timezone.now()
    all_notifs = _active_notifications_qs()
    filtered_notifs = []

    for n in all_notifs:
        val = n.filter_value

        if n.filter_type == "all":
            filtered_notifs.append(n)
        elif n.filter_type == "disease" and val in user_diseases:
            filtered_notifs.append(n)
        elif n.filter_type == "city" and user_city == val:
            filtered_notifs.append(n)
        elif n.filter_type == "user" and user_email == val:
            filtered_notifs.append(n)

    data_list = [_serialize_notification(x) for x in filtered_notifs]

    return Response({"success": True, "notifications": data_list}, status=200)