from django.db import migrations, models
import django.db.models.deletion


def clear_main_color_when_variants_exist(apps, schema_editor):
    Product = apps.get_model('iwm', 'Product')
    ProductColorImage = apps.get_model('iwm', 'ProductColorImage')
    product_ids = ProductColorImage.objects.values_list('product_id', flat=True).distinct()
    Product.objects.filter(id__in=product_ids, color__isnull=False).update(color=None)


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0019_productcolorimage'),
    ]

    operations = [
        migrations.RunPython(clear_main_color_when_variants_exist, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='MoreImages',
        ),
        migrations.AlterField(
            model_name='product',
            name='color',
            field=models.ForeignKey(
                blank=True,
                help_text='Optional color for the main image. Leave empty when using color-specific images.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='iwm.color',
            ),
        ),
    ]
