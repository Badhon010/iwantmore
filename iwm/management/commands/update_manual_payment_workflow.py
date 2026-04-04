from django.core.management.base import BaseCommand
from iwm.models import Order

class Command(BaseCommand):
    help = 'Updates existing orders to match the new manual payment workflow'

    def handle(self, *args, **options):
        # Update any orders that might have credit card as payment method to use a valid method
        orders = Order.objects.filter(payment_method='card')
        for order in orders:
            # Default to cash on delivery for any card orders since we removed card option
            order.payment_method = 'cash_on_delivery'
            order.save(update_fields=['payment_method'])
            self.stdout.write(
                self.style.SUCCESS(f'Updated order {order.id} from card to cash_on_delivery')
            )
        
        # Also update any orders with 'cod' to 'cash_on_delivery' for consistency
        cod_orders = Order.objects.filter(payment_method='cod')
        for order in cod_orders:
            order.payment_method = 'cash_on_delivery'
            order.save(update_fields=['payment_method'])
            self.stdout.write(
                self.style.SUCCESS(f'Updated order {order.id} from cod to cash_on_delivery')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully updated all orders to match new payment workflow')
        )