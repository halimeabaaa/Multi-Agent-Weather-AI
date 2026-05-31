# summary/models.py
from django.db import models
from django.conf import settings

class DailySummary(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_summaries')
    city = models.CharField(max_length=100)
    temp = models.FloatField()
    weather_type = models.CharField(max_length=50) # Örn: Clear, Clouds, Rain
    pollen = models.CharField(max_length=50, default="Normal") # Sprint 3'te dinamikleşecek
    risk_level = models.CharField(max_length=20, default="Düşük") # Sprint 3'te dinamikleşecek
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # En son üretilen özet en üstte gelsin

    def __str__(self):
        return f"{self.user.username} - {self.city} - {self.created_at.date()}"


# summary/models.py dosyasının en altına eklenecek:

class SystemLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="system_logs")
    action = models.CharField(max_length=255, verbose_name="Yapılan İşlem") # Örn: "AI Raporu Üretildi"
    details = models.TextField(verbose_name="İşlem Detayları") # Örn: "Malatya şehri için rapor tetiklendi."
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Adresi")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "system_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.action} ({self.created_at.strftime('%d.%m %H:%M')})"


# summary/models.py dosyasının en altına eklenecek:

# summary/models.py içindeki SystemNotification modelini bununla güncelliyoruz:

class SystemNotification(models.Model):
    DISPLAY_HEADING = "Kullanıcılarımızın Dikkatine"

    filter_type = models.CharField(max_length=50, default="all", verbose_name="Hedef kitle")
    filter_value = models.CharField(max_length=255, blank=True, null=True, verbose_name="Hedef değer")
    title = models.CharField(max_length=255, verbose_name="Konu (alt başlık)")
    message = models.TextField(verbose_name="Uyarı metni")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    expires_at = models.DateTimeField(verbose_name="Yayın bitiş zamanı")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "system_notifications"
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at