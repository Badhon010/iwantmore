from django.db import migrations, models


def set_buying_price(apps, schema_editor):
    Product = apps.get_model('iwm', 'Product')
    Product.objects.all().update(buying_price=500)


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0013_promobanner_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='buying_price',
            field=models.PositiveIntegerField(default=500),
        ),
        migrations.RunPython(set_buying_price, reverse_code=migrations.RunPython.noop),
    ]
