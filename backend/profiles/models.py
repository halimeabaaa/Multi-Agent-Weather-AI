from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    min_temp = models.IntegerField(null=True, blank=True, verbose_name="Min. sıcaklık tercihi")
    max_temp = models.IntegerField(null=True, blank=True, verbose_name="Max. sıcaklık tercihi")

    favorite_weather = models.JSONField(default=list, verbose_name="Sevilen hava türleri")
    disliked_weather = models.JSONField(default=list, verbose_name="Sevilmeyen hava türleri")
    activities = models.JSONField(default=list, verbose_name="Düzenli aktiviteler")

    blood_type = models.CharField(max_length=5, blank=True, default="", verbose_name="Kan grubu")
    medications = models.JSONField(default=list, verbose_name="Kullanılan ilaçlar")
    allergies = models.JSONField(default=list, verbose_name="Alerjiler")
    health_notes = models.TextField(blank=True, default="", verbose_name="Ek sağlık notları")

    is_onboarded = models.BooleanField(default=False, verbose_name="Profil tamamlandı mı?")

    def __str__(self):
        return self.user.username