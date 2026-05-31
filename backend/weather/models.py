from django.db import models
from django.conf import settings


class UserLocation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    lat = models.FloatField()
    lon = models.FloatField()

    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)


class WeatherSnapshot(models.Model):
    lat = models.FloatField()
    lon = models.FloatField()

    temp = models.FloatField()
    humidity = models.FloatField()
    wind = models.FloatField()

    uv = models.FloatField()
    pollen = models.CharField(max_length=20)
    air_quality = models.CharField(max_length=20)

    rain = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)