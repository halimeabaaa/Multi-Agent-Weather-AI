from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def set_default_expires(apps, schema_editor):
    SystemNotification = apps.get_model("summary", "SystemNotification")
    default_end = timezone.now() + timedelta(days=7)
    for row in SystemNotification.objects.filter(expires_at__isnull=True):
        row.expires_at = row.created_at + timedelta(days=7) if row.created_at else default_end
        row.save(update_fields=["expires_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("summary", "0005_remove_systemnotification_target_disease_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemnotification",
            name="expires_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Yayın bitiş zamanı",
            ),
        ),
        migrations.RunPython(set_default_expires, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="systemnotification",
            name="expires_at",
            field=models.DateTimeField(verbose_name="Yayın bitiş zamanı"),
        ),
    ]
