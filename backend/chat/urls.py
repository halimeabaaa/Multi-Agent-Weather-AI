# backend/chat/urls.py
from django.urls import path
from .views import send_chat_message_view, get_chat_history_view

app_name = 'chat'

urlpatterns = [
    path('send/', send_chat_message_view, name='send_message'),
    path('history/', get_chat_history_view, name='get_history'),
]