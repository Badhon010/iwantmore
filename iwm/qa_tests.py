import json
from decimal import Decimal
from datetime import timedelta
from unittest import mock
import threading

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.db import connection

from iwm.admin import OrderAdmin, admin_site
from iwm.models import Category, Coupon, Order, Product, SubCategory, OrderItem

class QAAuditTests(TransactionTestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user_model = get_user_model()
        self.category = Category.objects.create(name='QA Electronics')
        self.subcategory = SubCategory.objects.create(name='QA Phones', category=self.category)
        self.product = self._create_product(name='QA Phone A', price=1000, stock=5)
        self.product_two = self._create_product(name='QA Phone B', price=500, stock=1)
        self.coupon = self._valid_coupon(code='QASAVE10', usage_limit=1)
        self.user = self.user_model.objects.create_user(username='qa_user', email='qa@example.com', password='pass')

    def _create_product(self, *, name, price, stock):
        return Product.objects.create(
            name=name,
            description=f'{name} description',
            price=price,
            image=SimpleUploadedFile(f'{name}.jpg', b'filecontent', content_type='image/jpeg'),
            stock=stock,
            subcategory=self.subcategory,
        )

    def _valid_coupon(self, **overrides):
        defaults = {
            'code': 'SAVE10',
            'discount_percent': 10,
            'minimum_order_value': 0,
            'is_active': True,
            'valid_from': timezone.now() - timedelta(days=1),
            'valid_to': timezone.now() + timedelta(days=1),
            'usage_limit': 5,
        }
        defaults.update(overrides)
        return Coupon.objects.create(**defaults)
    
    def _create_order(self, **overrides):
        personal_info = overrides.pop('personal_info', {
            'full_name': 'QA Buyer',
            'email': 'buyer@example.com',
            'phone': '01722222222',
        })
        shipping_address_data = overrides.pop('shipping_address_data', {
            'full_name': 'QA Buyer',
            'address_line1': 'Street 1',
            'address_line2': 'Near the bus stand',
            'city': 'Dhaka',
            'postal_code': '1207',
            'state': 'Dhaka',
            'country': 'Bangladesh',
        })
        billing_address_data = overrides.pop('billing_address_data', shipping_address_data.copy())
        params = {
            'user': overrides.pop('user', None),
            'idempotency_key': overrides.pop('idempotency_key', f'idempotency-{timezone.now().timestamp()}'),
            'raw_items': overrides.pop('raw_items', [{'id': self.product.id, 'quantity': 1}]),
            'personal_info': personal_info,
            'shipping_address_data': shipping_address_data,
            'billing_address_data': billing_address_data,
            'same_billing_address': overrides.pop('same_billing_address', True),
            'payment_method': overrides.pop('payment_method', 'cash_on_delivery'),
            'sender_number': overrides.pop('sender_number', None),
            'transaction_id': overrides.pop('transaction_id', None),
            'delivery_payment_method': overrides.pop('delivery_payment_method', None),
            'delivery_sender_number': overrides.pop('delivery_sender_number', None),
            'delivery_transaction_id': overrides.pop('delivery_transaction_id', None),
            'notes': overrides.pop('notes', ''),
            'coupon_id': overrides.pop('coupon_id', None),
            'access_pin': overrides.pop('access_pin', ''),
        }
        params.update(overrides)
        return Order.create_order(**params)

    # PHASE 2: ORDER CREATION TESTS
    def test_successful_cod_order(self):
        order, created = self._create_order(payment_method='cash_on_delivery')
        self.assertTrue(created)
        self.assertEqual(order.payment_method, 'cash_on_delivery')
        self.assertEqual(order.payment_state, 'awaiting_payment')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)

    def test_successful_bkash_order(self):
        order, created = self._create_order(payment_method='bkash')
        self.assertTrue(created)
        self.assertEqual(order.payment_state, 'awaiting_payment')

    def test_guest_and_authenticated_orders(self):
        guest_order, _ = self._create_order(user=None)
        self.assertIsNone(guest_order.user)
        
        auth_order, _ = self._create_order(user=self.user)
        self.assertEqual(auth_order.user, self.user)

    # PHASE 3: INVENTORY INTEGRITY
    def test_cancel_then_refund_does_not_double_restore_stock(self):
        order, _ = self._create_order()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        
        order.transition_order_status('cancelled')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5) # Stock restored once
        
        # Now refund
        order.transition_payment_state('refunded')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5) # Should NOT increase to 6

    def test_concurrent_ordering_low_stock(self):
        # We have product_two with stock=1
        errors = []
        def purchase():
            try:
                self._create_order(
                    raw_items=[{'id': self.product_two.id, 'quantity': 1}],
                    idempotency_key=f'idemp-{threading.get_ident()}'
                )
            except ValidationError as e:
                errors.append(e)

        threads = [threading.Thread(target=purchase) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.product_two.refresh_from_db()
        # Should be exactly 0 stock, and 4 errors
        self.assertEqual(self.product_two.stock, 0)
        self.assertEqual(len(errors), 4)

    # PHASE 4: COUPON CONCURRENCY
    def test_coupon_over_limit(self):
        order1, _ = self._create_order(coupon_id=self.coupon.id, idempotency_key='c1')
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.used_count, 1)

        with self.assertRaises(ValidationError):
            self._create_order(coupon_id=self.coupon.id, idempotency_key='c2')

    # PHASE 5: PAYMENT VALIDATION
    def test_bkash_order_does_not_require_transaction_id(self):
        order, created = self._create_order(payment_method='bkash', sender_number='017111', transaction_id='')
        self.assertTrue(created)
        self.assertEqual(order.payment_state, 'awaiting_payment')

    def test_cod_fake_delivery_payment(self):
        with self.assertRaises(ValidationError):
            # Attempt to set delivery payment method but missing transaction id
            self._create_order(
                payment_method='cash_on_delivery',
                delivery_payment_method='bkash',
                delivery_sender_number='017111'
            )

    # PHASE 6: STATE MACHINE ATTACKS
    def test_illegal_transitions(self):
        order, _ = self._create_order()
        
        with self.assertRaises(ValidationError):
            order.transition_order_status('delivered') # pending -> delivered is illegal
            
        with self.assertRaises(ValidationError):
            order.transition_order_status('refunded') # pending -> refunded is illegal
            
        order.transition_order_status('cancelled')
        with self.assertRaises(ValidationError):
            order.transition_order_status('pending') # cancelled -> pending is illegal

    # PHASE 7: ADMIN PANEL TESTS
    def test_admin_bulk_actions(self):
        order, _ = self._create_order()
        staff_user = self.user_model.objects.create_superuser('admin2', 'admin@example.com', 'pass')
        request = self.factory.post('/admin/iwm/order/')
        request.user = staff_user
        order_admin = OrderAdmin(Order, admin_site)
        order_admin.message_user = lambda *args, **kwargs: None
        
        order_admin.mark_processing(request, Order.objects.filter(pk=order.pk))
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'processing')

    # PHASE 8: SECURITY TESTS
    def test_duplicate_requests_safe(self):
        order1, created1 = self._create_order(idempotency_key='sec-1')
        order2, created2 = self._create_order(idempotency_key='sec-1')
        
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(order1.id, order2.id)

    # PHASE 9: GUEST ORDER PIN RULES
    def test_guest_without_pin_cannot_cancel(self):
        order, _ = self._create_order(user=None, access_pin='')
        session = self.client.session
        session['authorized_order_ids'] = [order.id]
        session.save()
        
        self.client.post(reverse('cancel_order', args=[order.order_number]))
        order.refresh_from_db()
        # Should still be pending because no PIN
        self.assertEqual(order.order_status, 'pending')

    def test_guest_with_pin_can_cancel(self):
        order, _ = self._create_order(user=None, access_pin='1234')
        session = self.client.session
        session['authorized_order_ids'] = [order.id]
        session.save()
        
        self.client.post(reverse('cancel_order', args=[order.order_number]))
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'cancelled')
