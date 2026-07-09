from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('resellers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResellerApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=20)),
                ('whatsapp', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('store_name', models.CharField(blank=True, max_length=200)),
                ('store_address', models.TextField(blank=True)),
                ('outlet_type', models.CharField(blank=True, max_length=100)),
                ('bank_upi', models.CharField(blank=True, max_length=200)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                    default='pending', max_length=20,
                )),
                ('applied_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'ordering': ['-applied_at'],
            },
        ),
    ]
