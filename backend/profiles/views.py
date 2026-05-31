# profiles/views.py
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache  # 🎯 [DÜZELTME]: cache import edilerek 500 hatası kökten çözüldü!
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from health.models import HealthCondition, UserHealth
from summary.models import DailySummary
from .models import UserProfile
from .serializers import UserProfileSerializer
from .health_context import build_health_profile_dict, BLOOD_TYPE_CHOICES


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def save_onboarding(request):
    user = request.user
    
    # 🎯 [DÜZELTME]: OneToOne model güvenliği için DoesNotExist istisnası da eklendi
    try:
        profile = user.userprofile
        has_profile = True
    except (AttributeError, UserProfile.DoesNotExist):
        profile = None
        has_profile = False

    # POST atılıyorsa ve profil zaten varsa PUT'a yönlendir veya hata dön
    if request.method == 'POST' and has_profile:
        return Response(
            {"detail": "Bu kullanıcının zaten bir profili var. Güncelleme (PUT) yapmalısınız."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # PUT atılıyorsa ve profil henüz yoksa engelle
    if request.method == 'PUT' and not has_profile:
        return Response(
            {"detail": "Güncellenecek profil bulunamadı. Önce oluşturmalısınız."},
            status=status.HTTP_404_NOT_FOUND
        )

    diseases = request.data.get("diseases", None)
    mutable_data = request.data.copy()
    
    if "diseases" in mutable_data:
        mutable_data.pop("diseases")

    # Kullanıcı girişlerini aralık mantığına normalize ediyoruz: [min_temp, max_temp]
    min_temp = mutable_data.get("min_temp", None)
    max_temp = mutable_data.get("max_temp", None)
    if min_temp is not None and max_temp is not None and min_temp != "" and max_temp != "":
        try:
            min_val = float(min_temp)
            max_val = float(max_temp)
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            mutable_data["min_temp"] = min_val
            mutable_data["max_temp"] = max_val
        except (TypeError, ValueError):
            pass

    # Veriyi kaydet veya güncelle
    serializer = UserProfileSerializer(
        instance=profile, 
        data=mutable_data,
        context={'request': request},
        partial=True
    )
    
    if serializer.is_valid():
        with transaction.atomic():
            # Eğer ilk defa oluşturuluyorsa user bağlantısını garantiye alıyoruz
            if not has_profile:
                profile = serializer.save(user=user)
            else:
                serializer.save()
                
            if diseases is not None:
                sync_user_diseases(user, diseases)
                
            # Profil anketi değiştiyse, bugünün AI özetini geçersiz kıl.
            DailySummary.objects.filter(
                user=user,
                created_at__date=timezone.now().date(),
            ).delete()
            
        today_str = timezone.now().date().isoformat()
        cache.delete(f"ai_generating_{user.id}_{today_str}")
        
        msg = "Profil başarıyla güncellendi!" if has_profile else "Onboarding bilgileri kaydedildi!"
        return Response({"success": True, "message": msg, "data": serializer.data}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    serializer = UserProfileSerializer(profile, context={'request': request})
    
    health = build_health_profile_dict(request.user, profile)
    response_data = {
        "username": request.user.username,
        "email": request.user.email,
        "diseases": health["diseases"],
        "blood_type_choices": [{"value": v, "label": l} for v, l in BLOOD_TYPE_CHOICES],
        **serializer.data,
        "medications": health["medications"],
        "allergies": health["allergies"],
    }

    return Response(response_data, status=status.HTTP_200_OK)


def sync_user_diseases(user, diseases):
    """
    🎯 [DÜZELTME]: Gelen veri tipi string ise (Örn: "fitness,yüzme"), 
    bunu güvenle diziye/array'e çevirip patlamaları önler.
    """
    if isinstance(diseases, str):
        diseases = [d.strip() for d in diseases.split(',') if d.strip()]

    cleaned_names = []
    if isinstance(diseases, list):
        for item in diseases:
            value = str(item).strip()
            if value:
                cleaned_names.append(value)

    unique_names = list(dict.fromkeys(cleaned_names))

    UserHealth.objects.filter(user=user).exclude(
        condition__name__in=unique_names
    ).delete()

    for disease_name in unique_names:
        condition, _ = HealthCondition.objects.get_or_create(name=disease_name)
        UserHealth.objects.get_or_create(
            user=user,
            condition=condition,
            defaults={"severity": "medium"},
        )