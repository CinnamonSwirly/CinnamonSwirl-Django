# Generated by Django 4.1 on 2022-09-08 06:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CinnamonSwirl', '0008_reminder_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='end_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='reminder',
            name='routine_days',
            field=models.IntegerField(null=True),
        ),
    ]
