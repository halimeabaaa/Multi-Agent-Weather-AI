from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import HealthCondition, UserHealth


@api_view(['POST'])
def save_health(request):
    user = request.user

    conditions = request.data.get("conditions", [])

    UserHealth.objects.filter(user=user).delete()

    for item in conditions:
        condition_obj, _ = HealthCondition.objects.get_or_create(
            name=item["name"]
        )

        UserHealth.objects.create(
            user=user,
            condition=condition_obj,
            severity=item.get("severity", "low")
        )

    return Response({"message": "health saved"})