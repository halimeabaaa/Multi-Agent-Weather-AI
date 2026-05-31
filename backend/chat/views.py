# backend/chat/views.py
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

from .services import ask_ai_assistant
from .models import ChatMessage

@api_view(['POST'])
@permission_classes([IsAuthenticated]) # 🎯 Oturumu standart Django yerine JWT (Bearer) Token ile doğrular!
def send_chat_message_view(request):
    """
    JWT Token ile kimlik doğrulaması yapılmış kullanıcının mesajını alır,
    dinamik AI servisini tetikler ve sonucu döner.
    """
    try:
        # DRF kullanırken veriyi request.data üzerinden güvenle alabiliriz
        user_message = request.data.get("message", "").strip()

        if not user_message:
            return Response({"success": False, "error": "Mesaj boş olamaz."}, status=status.HTTP_400_BAD_REQUEST)

        # Akıllı asistan servisimizi tetikle 🚀
        ai_result = ask_ai_assistant(request.user, user_message)

        if ai_result.get("success"):
            return Response({
                "success": True,
                "response": ai_result.get("response")
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": ai_result.get("response", "Yapay zeka yanıt üretemedi.")
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({"success": False, "error": f"Sistem hatası: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_history_view(request):
    """
    Kullanıcının JWT Token'ına ait geçmiş sohbet kayıtlarını döner.
    """
    # Son 20 mesajı çekiyoruz
    messages = ChatMessage.objects.filter(user=request.user).order_by('created_at')[:20]
    
    history_data = []
    for msg in messages:
        history_data.append({
            "user_message": msg.user_message,
            "ai_response": msg.ai_response,
            "time": msg.created_at.strftime("%H:%M")
        })
        
    return Response({"success": True, "history": history_data}, status=status.HTTP_200_OK)