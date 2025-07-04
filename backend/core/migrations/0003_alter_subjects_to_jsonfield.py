from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_move_uuid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="game",
            name="subjects",
            field=models.JSONField(default=list, blank=True),
        ),
    ]
