# config/celery.py
import os
from celery import Celery

# Django ayarlarını Celery için varsayılan olarak ayarlıyoruz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('weather_ai')

# Django'nun settings.py dosyasındaki CELERY_ ile başlayan ayarları okutuyoruz
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tüm uygulamalardaki (tasks.py) arka plan görevlerini otomatik bulur
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')