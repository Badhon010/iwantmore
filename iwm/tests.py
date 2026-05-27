import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .admin import OrderAdmin, admin_site
from .models import Category, Coupon, Order, Product, SubCategory


class OrderWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user_model = get_user_model()

        self.category = Category.objects.create(name='Electronics')
        self.subcategory = SubCategory.objects.create(name='Phones', category=self.category)
        self.product = self._create_product(name='Phone A', price=1000, stock=5)
        self.product_two = self._create_product(name='Phone B', price=500, stock=6)

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

    def _order_payload(self, **overrides):
        payload = {
            'personal_info': {
                'full_name': 'Guest Buyer',
                'email': 'guest@example.com',
                'phone': '01711111111',
            },
            'shipping_address': {
                'full_name': 'Guest Buyer',
                'address_line1': 'Road 1',
                'address_line2': 'Near the main road',
                'city': 'Dhaka',
                'postal_code': '1207',
                'state': 'Dhaka',
                'country': 'Bangladesh',
            },
            'billing_address': {
                'full_name': 'Guest Buyer',
                'address_line1': 'Road 1',
                'address_line2': 'Near the main road',
                'city': 'Dhaka',
                'postal_code': '1207',
                'state': 'Dhaka',
                'country': 'Bangladesh',
            },
            'same_billing_address': True,
            'payment_method': 'cod',
            'payment_details': {},
            'items': [{'id': self.product.id, 'quantity': 2}],
            'additional_notes': '',
            'idempotency_key': 'checkout-1',
            'access_pin': '',
        }
        payload.update(overrides)
        return payload

    def _create_order(self, **overrides):
        personal_info = overrides.pop('personal_info', {
            'full_name': 'Buyer Name',
            'email': 'buyer@example.com',
            'phone': '01722222222',
        })
        shipping_address_data = overrides.pop('shipping_address_data', {
            'full_name': 'Buyer Name',
            'address_line1': 'Street 1',
            'address_line2': 'Near the market',
            'city': 'Dhaka',
            'postal_code': '1207',
            'state': 'Dhaka',
            'country': 'Bangladesh',
        })
        billing_address_data = overrides.pop('billing_address_data', shipping_address_data.copy())
        params = {
            'user': overrides.pop('user', None),
            'idempotency_key': overrides.pop('idempotency_key', f'idempotency-{timezone.now().timestamp()}'),
            'raw_items': overrides.pop('raw_items', [{'id': self.product.id, 'quantity': 2}]),
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

    def test_place_order_succeeds_and_deducts_stock_with_optional_pin(self):
        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._order_payload()),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')

        order = Order.objects.get(pk=payload['order_id'])
        self.product.refresh_from_db()

        self.assertEqual(order.payment_method, 'cash_on_delivery')
        self.assertEqual(order.access_pin_hash, '')
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.client.session.get('guest_order_id'), str(order.id))
        self.assertEqual(self.client.session.get('authorized_order_ids'), None)

    def test_order_cancellation_restores_stock_and_releases_coupon_once(self):
        coupon = self._valid_coupon()
        order, created = self._create_order(
            coupon_id=coupon.id,
            access_pin='1234',
            idempotency_key='coupon-order',
        )
        self.assertTrue(created)

        self.product.refresh_from_db()
        coupon.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(coupon.used_count, 1)

        order.transition_order_status('cancelled')
        self.product.refresh_from_db()
        coupon.refresh_from_db()

        self.assertEqual(order.order_status, 'cancelled')
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(coupon.used_count, 0)
        self.assertIsNotNone(order.inventory_restored_at)
        self.assertIsNotNone(order.coupon_usage_released_at)

        order.transition_payment_state('refunded')
        self.product.refresh_from_db()
        coupon.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(order.order_status, 'refunded')
        self.assertEqual(order.payment_state, 'refunded')
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(coupon.used_count, 0)

    def test_admin_cancel_action_uses_transition_logic(self):
        order, _ = self._create_order(idempotency_key='admin-cancel', access_pin='4321')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

        staff_user = self.user_model.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='strong-pass-123',
        )
        request = self.factory.post('/admin/iwm/order/')
        request.user = staff_user

        order_admin = OrderAdmin(Order, admin_site)
        order_admin.message_user = lambda *args, **kwargs: None
        order_admin.mark_cancelled(request, Order.objects.filter(pk=order.pk))

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.order_status, 'cancelled')
        self.assertEqual(self.product.stock, 5)

    def test_manual_wallet_order_can_be_created_without_payment_references(self):
        order, created = self._create_order(
            idempotency_key='manual-order-no-references',
            payment_method='bkash',
            raw_items=[{'id': self.product.id, 'quantity': 1}],
        )

        self.assertTrue(created)
        self.assertEqual(order.payment_method, 'bkash')
        self.assertEqual(order.payment_state, 'awaiting_payment')
        self.assertFalse(order.sender_number)
        self.assertFalse(order.transaction_id)

    def test_duplicate_transaction_id_is_rejected_case_insensitively(self):
        self._create_order(
            idempotency_key='manual-order-1',
            payment_method='bkash',
            sender_number='01733333333',
            transaction_id='ABC123',
            raw_items=[{'id': self.product.id, 'quantity': 1}],
        )

        with self.assertRaises(ValidationError):
            self._create_order(
                idempotency_key='manual-order-2',
                payment_method='nagad',
                sender_number='01744444444',
                transaction_id='abc123',
                raw_items=[{'id': self.product_two.id, 'quantity': 1}],
            )

    def test_guest_cancel_requires_saved_pin(self):
        pinned_order, _ = self._create_order(
            idempotency_key='guest-cancel-pinned',
            access_pin='5678',
            raw_items=[{'id': self.product.id, 'quantity': 1}],
        )
        no_pin_order, _ = self._create_order(
            idempotency_key='guest-cancel-no-pin',
            access_pin='',
            raw_items=[{'id': self.product_two.id, 'quantity': 1}],
        )

        session = self.client.session
        session['authorized_order_ids'] = [pinned_order.id, no_pin_order.id]
        session.save()

        self.client.post(reverse('cancel_order', args=[no_pin_order.id]))
        no_pin_order.refresh_from_db()
        self.assertEqual(no_pin_order.order_status, 'pending')

        self.client.post(reverse('cancel_order', args=[pinned_order.id]))
        pinned_order.refresh_from_db()
        self.assertEqual(pinned_order.order_status, 'cancelled')

    def test_illegal_order_transition_is_blocked(self):
        order, _ = self._create_order(idempotency_key='illegal-transition')

        with self.assertRaises(ValidationError):
            order.transition_order_status('shipped')

        order.refresh_from_db()
        self.assertEqual(order.order_status, 'pending')
