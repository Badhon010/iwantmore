from django.db import migrations, models


def populate_payment_state(apps, schema_editor):
    Order = apps.get_model('iwm', 'Order')

    for order in Order.objects.all().only(
        'id',
        'payment_status',
        'payment_method',
        'sender_number',
        'transaction_id',
        'delivery_charge_paid',
    ):
        if order.payment_status:
            payment_state = 'paid'
        elif order.delivery_charge_paid:
            payment_state = 'partially_paid'
        elif order.payment_method in {'bkash', 'nagad'} and (order.sender_number or order.transaction_id):
            payment_state = 'payment_submitted'
        else:
            payment_state = 'awaiting_payment'

        Order.objects.filter(pk=order.pk).update(payment_state=payment_state)


class Migration(migrations.Migration):

    dependencies = [
        ('iwm', '0007_order_access_pin_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_state',
            field=models.CharField(
                choices=[
                    ('awaiting_payment', 'Awaiting Payment'),
                    ('payment_submitted', 'Payment Submitted'),
                    ('partially_paid', 'Partially Paid'),
                    ('paid', 'Paid'),
                    ('failed', 'Failed'),
                    ('refunded', 'Refunded'),
                ],
                default='awaiting_payment',
                max_length=30,
            ),
        ),
        migrations.RunPython(populate_payment_state, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='order',
            name='payment_status',
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['created_at'], name='iwm_order_created_32e14d_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['order_status', 'created_at'], name='iwm_order_order_s_ab0fae_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['payment_state', 'created_at'], name='iwm_order_payment_a1304c_idx'),
        ),
    ]
