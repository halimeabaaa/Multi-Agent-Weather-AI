from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Giriş formunda e-posta veya kullanıcı adı kabul edilir."""

    def validate(self, attrs):
        identifier = (attrs.get("username") or "").strip()
        if "@" in identifier:
            try:
                user = User.objects.get(email__iexact=identifier)
                attrs["username"] = user.username
            except User.DoesNotExist:
                pass
        else:
            attrs["username"] = identifier
        return super().validate(attrs)
