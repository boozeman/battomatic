from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batteries', '0001_initial_squashed_0007_alter_battery_connector'),
    ]

    operations = [
        migrations.AlterField(
            model_name='battery',
            name='connector',
            field=models.CharField(
                choices=[
                    ('BT2.0', 'BT2.0'),
                    ('PH2.0', 'PH2.0'),
                    ('XT30', 'XT-30'),
                    ('XT60', 'XT-60'),
                    ('XT90', 'XT-90'),
                    ('JR/FUTABA', 'JR/Futaba'),

                ],
                default='XT30',
                max_length=10,
            ),
        ),
    ]
