from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.models import User
from django.contrib.auth.hashers import make_password

@api_view(['POST'])
@permission_classes([AllowAny]) # Herkese açık olmalı
def register_user(request):
    data = request.data
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    # 1. Alanların kontrolü
    if not username or not email or not password:
        return Response({"detail": "Lütfen tüm alanları doldurun."}, status=status.HTTP_400_BAD_REQUEST)

    if password != confirm_password:
        return Response({"detail": "Şifreler birbiriyle uyuşmuyor."}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Benzersizlik kontrolü
    if User.objects.filter(username=username).exists():
        return Response({"detail": "Bu kullanıcı adı zaten alınmış."}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({"detail": "Bu e-posta adresi zaten kayıtlı."}, status=status.HTTP_400_BAD_REQUEST)

    # 3. Kullanıcıyı güvenli şifreleme ile oluşturma
    try:
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password) # Şifreyi hash'liyoruz
        )
        return Response({"message": "user created"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = (request.data.get('email') or '').strip().lower()
    if not email:
        return Response(
            {"detail": "E-posta adresi gerekli."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.filter(email__iexact=email).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/reset-password.html"
            f"?uid={uid}&token={token}"
        )
        try:
            send_mail(
                subject="Weather AI — Şifre sıfırlama",
                message=(
                    "Merhaba,\n\n"
                    "Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın "
                    "(bağlantı kısa süre içinde geçerliliğini yitirir):\n\n"
                    f"{reset_url}\n\n"
                    "Bu isteği siz yapmadıysanız bu e-postayı yok sayabilirsiniz.\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as exc:
            if settings.DEBUG:
                print(f"[password-reset] E-posta hatası: {exc}")
            return Response(
                {
                    "detail": (
                        "E-posta gönderilemedi. backend/.env içinde Gmail SMTP ve "
                        "uygulama şifresini kontrol edin."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(
        {
            "detail": "Bu e-posta kayıtlıysa şifre sıfırlama bağlantısı gönderildi.",
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    uid = request.data.get('uid')
    token = request.data.get('token')
    password = request.data.get('password')
    confirm_password = request.data.get('confirm_password')

    if not all([uid, token, password, confirm_password]):
        return Response(
            {"detail": "Tüm alanlar zorunludur."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != confirm_password:
        return Response(
            {"detail": "Şifreler birbiriyle uyuşmuyor."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {"detail": "Şifre en az 8 karakter olmalıdır."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {"detail": "Geçersiz veya süresi dolmuş bağlantı."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(user, token):
        return Response(
            {"detail": "Geçersiz veya süresi dolmuş bağlantı."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(password)
    user.save()

    return Response(
        {"message": "Şifreniz güncellendi. Giriş yapabilirsiniz."},
        status=status.HTTP_200_OK,
    )