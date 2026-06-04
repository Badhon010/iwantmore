# Generated migration for order_number field

from django.db import migrations, models
import random
import string
from django.utils import timezone


def populate_order_numbers(apps, schema_editor):
    """Populate order_number for existing orders"""
    Order = apps.get_model('iwm', 'Order')
    
    for order in Order.objects.filter(order_number__exact='').order_by('id'):
        timestamp = order.created_at.strftime('%Y%m%d%H%M%S')
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order.order_number = f"ORD{timestamp}{random_suffix}"
        order.save(update_fields=['order_number'])


def reverse_populate(apps, schema_editor):
    """Reverse operation"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("iwm", "0022_product_images_optional_color_orderitem_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_number",
            field=models.CharField(default='', max_length=25),
        ),
        migrations.RunPython(populate_order_numbers, reverse_populate),
        migrations.AlterField(
            model_name="order",
            name="order_number",
            field=models.CharField(max_length=25, unique=True),
        ),
    ]
