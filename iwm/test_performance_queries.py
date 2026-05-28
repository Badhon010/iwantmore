from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from iwm.models import (
    AdminAlert,
    Brand,
    Category,
    Color,
    FeatureReason,
    Order,
    OrderItem,
    Product,
    Review,
    Size,
    SubCategory,
    Tag,
)


class PerformanceQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_model = get_user_model()
        cls.superuser = cls.user_model.objects.create_superuser(
            username='perf-admin',
            email='perf-admin@example.com',
            password='pass1234',
        )
        cls.review_user = cls.user_model.objects.create_user(
            username='reviewer',
            email='reviewer@example.com',
            password='pass1234',
        )

        cls.category = Category.objects.create(name='Electronics')
        cls.other_category = Category.objects.create(name='Accessories')
        cls.subcategory = SubCategory.objects.create(name='Phones', category=cls.category)
        cls.other_subcategory = SubCategory.objects.create(name='Cases', category=cls.other_category)
        cls.feature_reason = FeatureReason.objects.create(Reason='Editor Pick')
        cls.color = Color.objects.create(name='Black')
        cls.size = Size.objects.create(name='M')
        cls.brand = Brand.objects.create(name='Acme')
        cls.tag_one = Tag.objects.create(name='smart')
        cls.tag_two = Tag.objects.create(name='popular')

        image_file = lambda name: SimpleUploadedFile(name, b'filecontent', content_type='image/jpeg')

        cls.product = Product.objects.create(
            name='Main Product',
            description='Primary product',
            price=100,
            discount_price=90,
            image=image_file('main.jpg'),
            stock=5,
            subcategory=cls.subcategory,
            is_featured=True,
            feature_reason=cls.feature_reason,
            color=cls.color,
            size=cls.size,
            brand=cls.brand,
        )
        cls.product.tags.add(cls.tag_one, cls.tag_two)
        Review.objects.create(product=cls.product, user=cls.review_user, rating=5, comment='Excellent')
        Review.objects.create(product=cls.product, user=cls.review_user, rating=4, comment='Great')

        for index in range(1, 4):
            related = Product.objects.create(
                name=f'Related Product {index}',
                description='Related product',
                price=50 + index,
                image=image_file(f'related-{index}.jpg'),
                stock=4 + index,
                subcategory=cls.subcategory if index < 3 else cls.other_subcategory,
                color=cls.color,
                size=cls.size,
                brand=cls.brand,
            )
            if index < 3:
                related.tags.add(cls.tag_one)
            else:
                related.tags.add(cls.tag_two)
            Review.objects.create(product=related, user=cls.review_user, rating=4, comment='Nice')

        low_stock_products = []
        for index in range(1, 4):
            low_stock_product = Product.objects.create(
                name=f'Low Stock {index}',
                description='Low stock product',
                price=20 + index,
                image=image_file(f'low-stock-{index}.jpg'),
                stock=index,
                subcategory=cls.subcategory,
            )
            low_stock_products.append(low_stock_product)

        for index in range(1, 23):
            order = Order.objects.create(
                full_name=f'Buyer {index}',
                email=f'buyer{index}@example.com',
                phone='01700000000',
                total_price=Decimal('100.00') + index,
                original_price=Decimal('100.00') + index,
                shipping_cost=Decimal('0.00'),
                discount_amount=Decimal('0.00'),
                payment_state='paid',
                order_status='processing',
                payment_method='cash_on_delivery',
            )
            OrderItem.objects.create(
                order=order,
                product=cls.product,
                product_name=cls.product.name,
                product_price=cls.product.price,
                quantity=1,
            )

        stale_time = timezone.now() - timedelta(days=2)
        for index in range(1, 4):
            failed_order = Order.objects.create(
                full_name=f'Failed Buyer {index}',
                email=f'failed{index}@example.com',
                phone='01711111111',
                total_price=Decimal('250.00'),
                original_price=Decimal('250.00'),
                shipping_cost=Decimal('0.00'),
                discount_amount=Decimal('0.00'),
                payment_state='awaiting_payment',
                order_status='pending',
                payment_method='cash_on_delivery',
            )
            Order.objects.filter(pk=failed_order.pk).update(created_at=stale_time)
            failed_order.refresh_from_db()
            OrderItem.objects.create(
                order=failed_order,
                product=low_stock_products[index - 1],
                product_name=low_stock_products[index - 1].name,
                product_price=low_stock_products[index - 1].price,
                quantity=2,
            )

        AdminAlert.objects.create(
            alert_type='system',
            severity='info',
            title='System Alert',
            message='Informational alert',
        )

    def setUp(self):
        self.client = Client()

    def test_product_detail_queries(self):
        with self.assertNumQueries(6):
            response = self.client.get(reverse('product_detail', args=[self.product.slug]))

        self.assertEqual(response.status_code, 200)

        product = response.context['product']
        with self.assertNumQueries(0):
            list(product.tags.all())
            [review.user.username for review in product.reviews.all()]

    def test_admin_alerts_queries(self):
        self.client.force_login(self.superuser)

        with self.assertNumQueries(13):
            response = self.client.get(reverse('admin:alerts'))

        self.assertEqual(response.status_code, 200)

    def test_admin_analytics_queries(self):
        self.client.force_login(self.superuser)

        with self.assertNumQueries(34):
            response = self.client.get(reverse('admin:analytics'))

        self.assertEqual(response.status_code, 200)
