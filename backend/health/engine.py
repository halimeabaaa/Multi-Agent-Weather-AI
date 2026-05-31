# health/health_service.py (Eski engine.py yerine)
from .models import UserHealth

def get_user_health_context(user):
    """
    Kullanıcının veritabanındaki tüm kronik hastalıklarını ve 
    şiddet derecelerini yapay zekanın anlayacağı temiz bir metin haline getirir.
    """
    user_health_records = UserHealth.objects.filter(user=user)
    
    if not user_health_records.exists():
        return "Kullanıcının bilinen herhangi bir kronik rahatsızlığı yoktur."
        
    health_text = "Kullanıcının Kronik Sağlık Durumları:\n"
    for record in user_health_records:
        health_text += f"- {record.condition.name} (Şiddet Derecesi: {record.severity})\n"
        if record.notes:
            health_text += f"  (Kullanıcı Notu: {record.notes})\n"
            
    return health_text