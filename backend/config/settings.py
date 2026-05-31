import os
from pathlib import Path
from celery.schedules import crontab
from dotenv import load_dotenv

# Projenin ana dizini (backend klasörü)
BASE_DIR = Path(__file__).resolve().parent.parent

# .env dosyasını yükle
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Güvenlik için zorunlu gizli anahtar (Varsayılan olarak bir değer atandı, .env içinde varsa oradan okunur)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-123456789')

# Geliştirme aşaması ayarları
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Uygulama Tanımlamaları
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Üçüncü Parti Kütüphaneler
    'rest_framework',
    'corsheaders',
    'django_celery_beat',

    # Kendi Uygulamaların
    'users',
    'profiles.apps.ProfilesConfig',
    'health',
    'weather',
    'summary',
    'chat',
    'calendar_app',
]

# Özel Kullanıcı Modeli
AUTH_USER_MODEL = "users.User"

# URL ve WSGI Yapılandırması (Hatanın çözümü için kritik olan kısım)
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# Ara Katmanlar (Middleware)
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Veritabanı Yapılandırması (MySQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT", "3306"),
    }
}

# Şablon Motoru (Templates)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], 
        'APP_DIRS': True, 
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Django REST Framework Ayarları
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

# Dil ve Zaman Ayarları (Standart Türkiye Yapılandırması)
LANGUAGE_CODE = 'tr-tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# Statik Dosya Yapılandırmaları
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Birincil Anahtar Tipi
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# config/settings.py en altına ekleyin:

# Celery ve Redis Bağlantı Ayarları
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE # Django'nun zaman dilimini kullansın

# Django Celery Beat Zamanlayıcı Kurulumu
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    "generate-daily-ai-summary-every-morning": {
        "task": "summary.tasks.generate_all_users_daily_summary",
        "schedule": crontab(hour=7, minute=0),
    }
}

# INSTALLED_APPS listesine de ekleme yapmalıyız!
# settings.py içindeki INSTALLED_APPS listesinin içine şu satırı ekle:
# 'django_celery_beat',


CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# Live Server / Vite gibi farklı portlardan gelen istekler (sadece geliştirme)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]

CORS_ALLOW_CREDENTIALS = True

# Frontend (şifre sıfırlama linki — Docker nginx: 3000, Live Server: 5500)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# E-posta / SMTP (Gmail uygulama şifresi → backend/.env)
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    EMAIL_HOST_USER or 'Weather AI <noreply@weatherai.local>',
)
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '30'))

# AI mikroservis endpoint'i
AI_SUMMARY_URL = os.getenv("AI_SUMMARY_URL", "http://fastapi:8005/api/v1/generate-summary")

# backend/config/settings.py
# Frontend origin adresini güvenilir kaynak olarak tescilliyoruz 🔒
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]