# health/models.py
from django.db import models
from django.conf import settings

class HealthCondition(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class UserHealth(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    condition = models.ForeignKey(HealthCondition, on_delete=models.CASCADE)
    severity = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ]
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.condition.name} ({self.severity})"


# PROJEYE ZARAR VERMEDEN SADECE BU YENİ KURAL TABLOSUNU EN ALTA EKLEDİK:
class HealthKnowledge(models.Model):
    """Hangi hastalığın hangi hava durumunda risk teşkil ettiğinin tıbbi kural tablosu"""
    condition_name = models.CharField(max_length=100) # Örn: Astım, Bronşit
    trigger_factor = models.CharField(max_length=100) # Örn: High Pollen, Extreme Cold
    recommendation = models.TextField() # Örn: "Maske takmayı unutmayın."

    def __str__(self):
        return f"{self.condition_name} -> {self.trigger_factor}"