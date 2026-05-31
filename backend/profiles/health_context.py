"""AI ve yönetim paneli için birleşik sağlık profil verisi."""
from health.models import UserHealth


BLOOD_TYPE_CHOICES = [
    ("", "Belirtilmemiş"),
    ("A+", "A Rh+"),
    ("A-", "A Rh-"),
    ("B+", "B Rh+"),
    ("B-", "B Rh-"),
    ("AB+", "AB Rh+"),
    ("AB-", "AB Rh-"),
    ("0+", "0 Rh+"),
    ("0-", "0 Rh-"),
]


def _clean_list(values):
    if not values:
        return []
    if isinstance(values, str):
        values = [v.strip() for v in values.split(",")]
    return [str(v).strip() for v in values if v and str(v).strip()]


def get_user_condition_names(user):
    return list(
        UserHealth.objects.filter(user=user)
        .select_related("condition")
        .values_list("condition__name", flat=True)
    )


def build_health_profile_dict(user, profile=None):
    """Profil + UserHealth kayıtlarını AI/chat/özet için tek sözlükte toplar."""
    if profile is None:
        from .models import UserProfile
        try:
            profile = UserProfile.objects.get(user=user)
        except Exception:
            profile = None

    diseases = get_user_condition_names(user)
    data = {
        "blood_type": "",
        "medications": [],
        "allergies": [],
        "health_notes": "",
        "min_temp": None,
        "max_temp": None,
        "favorite_weather": [],
        "disliked_weather": [],
        "activities": [],
        "diseases": diseases,
    }

    if profile:
        data.update({
            "blood_type": profile.blood_type or "",
            "medications": _clean_list(profile.medications),
            "allergies": _clean_list(profile.allergies),
            "health_notes": (profile.health_notes or "").strip(),
            "min_temp": profile.min_temp,
            "max_temp": profile.max_temp,
            "favorite_weather": _clean_list(profile.favorite_weather),
            "disliked_weather": _clean_list(profile.disliked_weather),
            "activities": _clean_list(profile.activities),
        })

    return data
