# backend/chat/services.py
import requests
from django.conf import settings

from .models import ChatMessage
from .context_builder import build_chat_context


def ask_ai_assistant(user, user_message_text):
    """Profil, takvim, saatlik hava ve uyarıların tamamını AI sohbetine iletir."""

    context = build_chat_context(user)

    history_list = []
    past_messages = ChatMessage.objects.filter(user=user).order_by("-created_at")[:6]
    for msg in reversed(past_messages):
        history_list.append({"role": "user", "content": msg.user_message})
        history_list.append({"role": "assistant", "content": msg.ai_response})

    fastapi_payload = {
        "user_profile": context["user_profile"],
        "weather_data": context["weather_data"],
        "calendar_events": context["calendar_events"],
        "reference_datetime": context["reference_datetime"],
        "history": history_list + [{"role": "user", "content": user_message_text}],
    }

    fastapi_url = getattr(settings, "AI_CHAT_URL", "http://fastapi:8005/api/v1/chat")

    try:
        response = requests.post(fastapi_url, json=fastapi_payload, timeout=30)
    except requests.RequestException:
        return {"success": False, "response": "Yapay zeka servisine bağlanılamadı."}

    if response.status_code == 200:
        result = response.json()
        ai_answer = result.get("response")
        ChatMessage.objects.create(
            user=user,
            user_message=user_message_text,
            ai_response=ai_answer,
        )
        return {"success": True, "response": ai_answer}

    return {"success": False, "response": "Yapay zeka motorundan yanıt alınamadı."}
