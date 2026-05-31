# calendar_app/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import CalendarEvent
from .serializers import CalendarEventSerializer

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def event_list_create_view(request):
    """
    GET: Kullanıcının tüm etkinliklerini kronolojik listeler.
    POST: Giriş yapmış kullanıcı adına yeni bir takvim etkinliği ekler.
    """
    if request.method == 'GET':
        now = timezone.now()
        # Tarihi geçmiş etkinlikleri otomatik temizle
        CalendarEvent.objects.filter(user=request.user, end_datetime__lt=now).delete()
        events = CalendarEvent.objects.filter(
            user=request.user,
            end_datetime__gte=now,
        ).order_by("start_datetime")
        serializer = CalendarEventSerializer(events, many=True)
        return Response({"success": True, "events": serializer.data}, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = CalendarEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            
            # Yeni bir etkinlik eklendiğinde, bugünün AI özetini siliyoruz ki
            # asistan yeni eklenen etkinliği hemen fark edip analize eklesin!
            today = timezone.now().date()
            from summary.models import DailySummary
            from django.core.cache import cache
            DailySummary.objects.filter(user=request.user, created_at__date=today).delete()
            cache.delete(f"ai_generating_{request.user.id}_{today.isoformat()}")

            return Response({"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def event_delete_view(request, pk):
    """
    DELETE: Belirtilen ID'ye sahip etkinliği güvenle siler.
    """
    try:
        event = CalendarEvent.objects.get(pk=pk, user=request.user)
    except CalendarEvent.DoesNotExist:
        return Response({"success": False, "error": "Etkinlik bulunamadı veya yetkiniz yok."}, status=status.HTTP_404_NOT_FOUND)

    event.delete()
    
    today = timezone.now().date()
    from summary.models import DailySummary
    from django.core.cache import cache
    DailySummary.objects.filter(user=request.user, created_at__date=today).delete()
    cache.delete(f"ai_generating_{request.user.id}_{today.isoformat()}")

    return Response({"success": True, "message": "Etkinlik başarıyla silindi."}, status=status.HTTP_200_OK)