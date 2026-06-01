# Generated manually after switching product media to image rows.

from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_product_images(apps, schema_editor):
    Product = apps.get_model('iwm', 'Product')
    ProductColorImage = apps.get_model('iwm', 'ProductColorImage')

    for product in Product.objects.exclude(image=''):
        if not product.image:
            continue
        if product.color_id and ProductColorImage.objects.filter(
            product_id=product.id,
            color_id=product.color_id,
        ).exists():
            continue

        ProductColorImage.objects.create(
            product_id=product.id,
            color_id=product.color_id,
            image=product.image,
        )

    Product.objects.exclude(image='').update(image=None, color_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0021_alter_coupon_options_alter_coupon_discount_amount_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='productcolorimage',
            name='unique_product_color_image',
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='product_images/'),
        ),
        migrations.AlterField(
            model_name='product',
            name='color',
            field=models.ForeignKey(
                blank=True,
                help_text='Legacy fallback only. Use product images below for new products.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='iwm.color',
            ),
        ),
        migrations.AlterField(
            model_name='productcolorimage',
            name='color',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='product_images',
                to='iwm.color',
            ),
        ),
        migrations.RunPython(copy_legacy_product_images, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='productcolorimage',
            constraint=models.UniqueConstraint(
                fields=('product', 'color'),
                name='unique_product_color_image',
            ),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='product_color',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
    ]
