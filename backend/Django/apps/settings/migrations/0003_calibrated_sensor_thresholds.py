from django.db import migrations


def set_calibrated_thresholds(apps, schema_editor):
    SystemSetting = apps.get_model('settings', 'SystemSetting')
    values = {
        'normal_threshold': ('0', 'Normal below the 2 cm Warning boundary'),
        'warning_threshold': ('2', 'Warning begins at 2 cm'),
        'danger_threshold': ('3', 'Critical/Danger begins at 3 cm'),
    }

    for key, (value, description) in values.items():
        SystemSetting.objects.update_or_create(
            key=key,
            defaults={'value': value, 'description': description},
        )

    SystemSetting.objects.filter(key='alert_threshold').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('settings', '0002_align_arduino_thresholds'),
    ]

    operations = [
        migrations.RunPython(set_calibrated_thresholds, migrations.RunPython.noop),
    ]