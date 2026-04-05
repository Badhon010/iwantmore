from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0006_address_user_nullable_order_idempotency_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='access_pin_hash',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
