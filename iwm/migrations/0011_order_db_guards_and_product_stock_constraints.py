from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0010_order_coupon_order_coupon_usage_released_at_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(
                condition=Q(stock__gte=0),
                name='product_stock_gte_0',
            ),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['created_at'], name='iwm_product_created_4ce980_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['stock'], name='iwm_product_stock_8ca593_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['order_status'], name='iwm_order_order_s_927712_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['payment_state'], name='iwm_order_payment_5ce184_idx'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.UniqueConstraint(
                Lower('transaction_id'),
                condition=Q(transaction_id__isnull=False) & ~Q(transaction_id=''),
                name='order_transaction_id_ci_unique',
            ),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.UniqueConstraint(
                Lower('delivery_transaction_id'),
                condition=Q(delivery_transaction_id__isnull=False) & ~Q(delivery_transaction_id=''),
                name='order_delivery_transaction_id_ci_unique',
            ),
        ),
    ]
