# Generated for Batt-o-matic 1.0
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Battery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(choices=[('IN_USE', 'In Use'), ('DECOMMISSIONED', 'Decommissioned')], default='IN_USE', max_length=20)),
                ('chemistry', models.CharField(choices=[('LIPO', 'LiPo'), ('LIHV', 'LiHV'), ('LIION', 'Li-Ion'), ('LIFE', 'Li-Fe'), ('NICD', 'NiCd'), ('NIMH', 'NiMh')], max_length=20)),
                ('purchase_date', models.DateField(blank=True, null=True)),
                ('manufacturer', models.CharField(blank=True, max_length=120)),
                ('model', models.CharField(max_length=120)),
                ('cell_count', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(24)])),
                ('c_rating', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='C rating')),
                ('capacity_mah', models.PositiveIntegerField(verbose_name='Capacity (mAh)')),
            ],
            options={'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='ChargeEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('event', models.CharField(choices=[('CHARGE', 'Charge'), ('STORAGE', 'Storage'), ('BALANCE', 'Balance'), ('DISCHARGE', 'Discharge')], max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('battery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='charge_events', to='batteries.battery')),
            ],
            options={'ordering': ['-date', '-id']},
        ),
        migrations.CreateModel(
            name='CellVoltage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cell_index', models.PositiveSmallIntegerField()),
                ('voltage', models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cell_voltages', to='batteries.chargeevent')),
            ],
            options={'ordering': ['cell_index'], 'unique_together': {('event', 'cell_index')}},
        ),
    ]
