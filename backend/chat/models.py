# backend/chat/models.py
from django.db import models
from django.conf import settings  # 👈 settings'i içeri alıyoruz

class ChatMessage(models.Model):
    """
    Kullanıcı ve Yapay Zeka (Bot) arasındaki mesajlaşma geçmişini tutan tablo.
    """
    # Standart User yerine dinamik olarak projedeki Custom User modelini bağlıyoruz 🎯
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="chat_messages"
    )
    user_message = models.TextField(verbose_name="Kullanıcının Sorusu")
    ai_response = models.TextField(verbose_name="Yapay Zeka Yanıtı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Mesaj Tarihi")

    class Meta:
        ordering = ['created_at']
        verbose_name = "Sohbet Mesajı"
        verbose_name_plural = "Sohbet Mesajları"

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"