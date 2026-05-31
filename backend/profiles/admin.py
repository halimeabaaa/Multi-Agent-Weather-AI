# profiles/admin.py
from django.contrib import admin
from .models import UserProfile

# UserProfile modelini admin paneline kaydediyoruz
admin.site.register(UserProfile)