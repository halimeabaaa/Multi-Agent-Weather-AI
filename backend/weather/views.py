# weather/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import UserLocation
from .services import get_weather_data, search_cities

@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Giriş zorunlu hale getirildi, böylece request.user güvende
def save_location(request):
    user = request.user

    lat = request.data.get("lat")
    lon = request.data.get("lon")
    city = request.data.get("city")
    country = request.data.get("country")

    # Kullanıcıya ait konum varsa günceller, yoksa yenisini oluşturur
    obj, created = UserLocation.objects.update_or_create(
        user=user,
        defaults={
            "lat": lat,
            "lon": lon,
            "city": city,
            "country": country
        }
    )

    return Response({"message": "Konum bilgisi başarıyla kaydedildi."}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def current_weather(request):
    # URL'den şehir parametresini alıyoruz (Örn: ?city=Istanbul)
    city = request.query_params.get('city')
    
    if not city:
        return Response({"detail": "Lütfen bir şehir ismi belirtin (?city=sehir)"}, status=status.HTTP_400_BAD_REQUEST)
        
    weather_result = get_weather_data(city)
    
    if weather_result["success"]:
        return Response(weather_result, status=status.HTTP_200_OK)
        
    return Response({"detail": weather_result["message"]}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def geocode_city_search(request):
    """Şehir adı araması (büyük/küçük harf ve Türkçe karakter duyarsız filtre ön yüzde de yapılır)."""
    q = request.query_params.get("q", "")
    cities = search_cities(q, limit=10)
    return Response({"success": True, "cities": cities}, status=status.HTTP_200_OK)