# health/admin.py
from django.contrib import admin
from .models import HealthCondition, UserHealth

admin.site.register(HealthCondition)
admin.site.register(UserHealth)