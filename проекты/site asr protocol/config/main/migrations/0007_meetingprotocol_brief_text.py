from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0006_meetingprotocol"),
    ]

    operations = [
        migrations.AddField(
            model_name="meetingprotocol",
            name="brief_text",
            field=models.TextField(blank=True, default=""),
        ),
    ]
