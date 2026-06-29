from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0025_slider_remove_product_brand_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='access_pin_hash',
        ),
    ]
