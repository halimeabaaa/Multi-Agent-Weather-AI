# profiles/serializers.py
from rest_framework import serializers
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        # Formda gördüğün tüm alanları API'ye açıyoruz
        fields = [
            'min_temp', 'max_temp',
            'favorite_weather', 'disliked_weather', 'activities',
            'blood_type', 'medications', 'allergies', 'health_notes',
            'is_onboarded',
        ]
        
    def create(self, validated_data):
        # İstekte bulunan mevcut kullanıcıyı otomatik olarak profile bağlıyoruz
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)