# calendar_app/serializers.py
from rest_framework import serializers
from .models import CalendarEvent

class CalendarEventSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'user', 'title', 'description', 
            'location', 'start_datetime', 'end_datetime', 'created_at'
        ]

    def validate(self, data):
        """
        Bitiş zamanının başlangıç zamanından önce olmasını engelleyen iş kuralı 🛡️
        """
        if data['start_datetime'] > data['end_datetime']:
            raise serializers.ValidationError(
                {"end_datetime": "Bitiş zamanı, başlangıç zamanından önce olamaz."}
            )
        return data