from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("iwm", "0018_remove_order_prevent_duplicate_transaction_ids_in_order_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductColorImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="product_images/")),
                ("color", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_images", to="iwm.color")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="color_images", to="iwm.product")),
            ],
            options={
                "ordering": ["color__name", "id"],
                "constraints": [
                    models.UniqueConstraint(fields=("product", "color"), name="unique_product_color_image"),
                ],
            },
        ),
    ]
