# calendar_app/models.py
from django.db import models
from django.conf import settings

class CalendarEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="calendar_events"
    )
    title = models.CharField(max_length=255, verbose_name="Etkinlik Başlığı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Etkinlik Yeri")
    
    start_datetime = models.DateTimeField(verbose_name="Başlangıç Zamanı")
    end_datetime = models.DateTimeField(verbose_name="Bitiş Zamanı")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calendar_events"
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.start_datetime.strftime('%d.%m %H:%M')})"