from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_meetingprotocol_brief_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="transcription",
            name="protocol_status",
            field=models.CharField(
                choices=[
                    ("not_started", "Не запущено"),
                    ("processing", "Выполняется"),
                    ("completed", "Завершено"),
                    ("failed", "Ошибка"),
                ],
                default="not_started",
                max_length=20,
            ),
        ),
    ]
