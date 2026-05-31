from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="blood_type",
            field=models.CharField(
                blank=True,
                default="",
                max_length=5,
                verbose_name="Kan grubu",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="medications",
            field=models.JSONField(default=list, verbose_name="Kullanılan ilaçlar"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="allergies",
            field=models.JSONField(default=list, verbose_name="Alerjiler"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="health_notes",
            field=models.TextField(blank=True, default="", verbose_name="Ek sağlık notları"),
        ),
    ]
