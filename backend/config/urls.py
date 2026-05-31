from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.views import register_user, request_password_reset, confirm_password_reset
from users.serializers import EmailOrUsernameTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register/', register_user, name='register_user'),
    path('api/auth/password/forgot/', request_password_reset, name='password_forgot'),
    path('api/auth/password/reset/', confirm_password_reset, name='password_reset'),
    path('api/profiles/', include('profiles.urls')),
    path('api/weather/', include('weather.urls')),
    path('api/health/', include('health.urls')),
    path('api/token/', CustomTokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/summary/', include('summary.urls')),
    path('api/chat/', include('chat.urls')),
    path('api/calendar/', include('calendar_app.urls')),

]