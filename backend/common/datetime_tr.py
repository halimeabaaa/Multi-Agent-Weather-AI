"""Türkiye saat diliminde tarih/saat metinleri (AI takvim bağlamı)."""
from django.utils import timezone

TR_MONTHS = (
    "",
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
)

TR_WEEKDAYS = (
    "Pazartesi",
    "Salı",
    "Çarşamba",
    "Perşembe",
    "Cuma",
    "Cumartesi",
    "Pazar",
)


def local_now():
    return timezone.localtime(timezone.now())


def format_tr_date(dt):
    local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
    month = TR_MONTHS[local.month]
    weekday = TR_WEEKDAYS[local.weekday()]
    return f"{local.day} {month} {local.year} {weekday}"


def format_tr_time(dt):
    local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
    return local.strftime("%H:%M")


def build_reference_datetime_context():
    """Sohbet/özet için kesin 'bugün' bilgisi — model kendi tarihini uydurmasın."""
    now = local_now()
    return {
        "iso_date": now.strftime("%Y-%m-%d"),
        "today_label": format_tr_date(now),
        "now_time": format_tr_time(now),
        "timezone": "Europe/Istanbul",
    }
