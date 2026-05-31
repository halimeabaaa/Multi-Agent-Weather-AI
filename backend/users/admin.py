# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Özel kullanıcı modelini admin paneline kaydediyoruz
admin.site.register(User, UserAdmin)