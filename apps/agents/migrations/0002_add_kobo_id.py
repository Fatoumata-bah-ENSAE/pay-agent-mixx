from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='creationmarchand',
            name='kobo_id',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='ID Kobo'),
        ),
        migrations.AddField(
            model_name='suivimarchand',
            name='kobo_id',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='ID Kobo'),
        ),
    ]
