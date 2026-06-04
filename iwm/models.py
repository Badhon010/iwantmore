from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q, Sum
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.urls import reverse
import json
import random
import string

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name
class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class SubCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.category.name}-{self.name}"
    
    class Meta:
        verbose_name_plural = "Subcategories"

class FeatureReason(models.Model):
    Reason = models.CharField(max_length=255)
    
    def __str__(self):
        return self.Reason

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Size(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.PositiveIntegerField()
    buying_price = models.PositiveIntegerField()
    discount_price = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)  
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField('Tag', related_name="products", blank=True)  
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, editable=False, related_name='products')
    subcategory = models.ForeignKey('SubCategory', on_delete=models.SET_NULL, null=True, related_name='products')
    is_featured = models.BooleanField(default=False)
    feature_reason = models.ForeignKey('FeatureReason', on_delete=models.SET_NULL, null=True, blank=True, related_name='featured_products')
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Legacy fallback only. Use product images below for new products.",
    )
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    # SEO fields
    meta_title = models.CharField(max_length=255, blank=True, null=True, help_text="SEO Meta Title")
    meta_description = models.TextField(blank=True, null=True, help_text="SEO Meta Description")

    def save(self, *args, **kwargs):
        if self.subcategory and self.subcategory.category:
            self.category = self.subcategory.category  # SubCategory থেকে Category স্বয়ংক্রিয়ভাবে সেট করো
        if not self.slug:
            self.slug = slugify(self.name)  
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name  

    def get_final_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def is_out_of_stock(self):
        return self.stock == 0

    @property
    def discount_percentage(self):
        try:
            if self.discount_price and self.price > 0:
                return round(100 - (self.discount_price / self.price) * 100, 2)
        except (TypeError, ZeroDivisionError):
            pass
        return 0

    @property
    def is_popular(self):
        return self.stock < 10  # আপনি শর্ত কাস্টমাইজ করতে পারেন

    def get_absolute_url(self):
        """ পণ্যের বিস্তারিত পেজের URL তৈরি করে """
        return f"/product/{self.slug}/"

    def get_prefetched_color_images(self):
        prefetched = getattr(self, '_prefetched_objects_cache', {})
        if 'color_images' in prefetched:
            return list(prefetched['color_images'])
        return list(self.color_images.select_related('color').all())

    def get_color_image(self, color_name=None):
        normalized_color = (color_name or '').strip().lower()
        if not normalized_color:
            return None

        for color_image in self.get_prefetched_color_images():
            if color_image.color and color_image.color.name.lower() == normalized_color:
                return color_image

        return None

    def get_primary_image(self):
        first_color_image = next(iter(self.get_prefetched_color_images()), None)
        if first_color_image and first_color_image.image:
            return first_color_image.image
        return self.image

    def get_available_color_names(self):
        color_names = []
        seen = set()

        for color_image in self.get_prefetched_color_images():
            if color_image.color and color_image.color.name not in seen:
                color_names.append(color_image.color.name)
                seen.add(color_image.color.name)

        if self.color and self.color.name not in seen:
            color_names.append(self.color.name)

        return color_names

    def requires_color_selection(self):
        return len(self.get_available_color_names()) > 1

    def update_stock(self, quantity_change):
        """
        Update product stock level
        
        Args:
            quantity_change: Integer indicating change in quantity (positive for increase, negative for decrease)
        
        Returns:
            Boolean: True if update was successful, False if there's not enough stock
        """
        if not self.pk:
            return False

        try:
            quantity_change = int(quantity_change)
        except (TypeError, ValueError):
            return False

        if quantity_change == 0:
            return True

        queryset = Product.objects.filter(pk=self.pk)
        if quantity_change < 0:
            updated = queryset.filter(stock__gte=abs(quantity_change)).update(stock=F('stock') + quantity_change)
        else:
            updated = queryset.update(stock=F('stock') + quantity_change)

        if not updated:
            return False

        self.refresh_from_db(fields=['stock'])
        return True

    def reserve_stock(self, quantity):
        try:
            quantity = abs(int(quantity))
        except (TypeError, ValueError):
            return False
        return self.update_stock(-quantity)

    def restore_stock(self, quantity):
        try:
            quantity = abs(int(quantity))
        except (TypeError, ValueError):
            return False
        return self.update_stock(quantity)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(stock__gte=0),
                name='product_stock_gte_0',
            ),
        ]
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['stock']),
        ]

class ProductColorImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='color_images',
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_images',
    )
    image = models.ImageField(upload_to='product_images/')

    class Meta:
        ordering = ['color__name', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'color'],
                name='unique_product_color_image',
            ),
        ]

    def __str__(self):
        label = self.color.name if self.color else 'Image'
        return f"{self.product.name} - {label}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='reviews')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def reviewer_name(self):
        return self.user.username if self.user else "Guest"

    def __str__(self):
        return f"Review by {self.reviewer_name()} for {self.product.name} - {self.rating}★"
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)  # New Field
    bio = models.TextField(blank=True)  # New Field

    def __str__(self):
        return self.user.username

class UserVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Automatically records the time when the record is created (i.e. when the verification email is sent)
    verification_sent_at = models.DateTimeField(auto_now_add=True)
    # This flag should be set to True when the user clicks your verification link
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} - Verified: {self.verified}'

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=50, blank=True, null=True, help_text="Which page the user subscribed from")
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"
    
    def __str__(self):
        return self.email

class Address(models.Model):
    ADDRESS_TYPES = (
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses', null=True, blank=True)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES)
    default = models.BooleanField(default=False)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Bangladesh')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.full_name} - {self.address_line1}, {self.city}"
    
    def save(self, *args, **kwargs):
        if self.default:
            # If this address is set as default, unset default for other addresses of same type for this user
            if self.user:
                Address.objects.filter(
                    user=self.user,
                    address_type=self.address_type,
                    default=True
                ).update(default=False)
        super().save(*args, **kwargs)
    
    @property
    def as_json(self):
        """Return address as JSON string for use in templates"""
        return json.dumps({
            'full_name': self.full_name,
            'phone': self.phone,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2 or '',
            'city': self.city,
            'postal_code': self.postal_code,
            'state': self.state,
            'country': self.country,
        })

    class Meta:
        verbose_name_plural = "Addresses"

class Order(models.Model):
    MANUAL_PAYMENT_METHODS = {'bkash', 'nagad'}
    TERMINAL_STATUSES = {'cancelled', 'refunded'}
    MONEY_QUANTIZER = Decimal('0.01')
    INSIDE_DHAKA_SHIPPING = Decimal('80.00')
    OUTSIDE_DHAKA_SHIPPING = Decimal('150.00')

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cash_on_delivery', 'Cash on Delivery'),
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
    )

    PAYMENT_STATE_CHOICES = (
        ('awaiting_payment', 'Awaiting Payment'),
        ('payment_submitted', 'Payment Submitted'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    DELIVERY_PAYMENT_METHOD_CHOICES = (
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
    )

    ORDER_STATUS_TRANSITIONS = {
        'pending': {'processing', 'cancelled'},
        'processing': {'shipped', 'cancelled', 'refunded'},
        'shipped': {'delivered', 'refunded'},
        'delivered': {'refunded'},
        'cancelled': {'refunded'},
        'refunded': set(),
    }

    PAYMENT_STATE_TRANSITIONS = {
        'awaiting_payment': {'payment_submitted', 'partially_paid', 'paid', 'failed', 'refunded'},
        'payment_submitted': {'partially_paid', 'paid', 'failed', 'refunded'},
        'partially_paid': {'paid', 'failed', 'refunded'},
        'paid': {'refunded'},
        'failed': {'payment_submitted', 'paid', 'refunded'},
        'refunded': set(),
    }
    order_number = models.CharField(max_length=25, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    idempotency_key = models.CharField(max_length=64, unique=True, blank=True, null=True)
    access_pin_hash = models.CharField(max_length=255, blank=True, default='')

    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=20)

    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='shipping_orders')
    billing_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='billing_orders')

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    order_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash_on_delivery')

    # Payment info (for full payment or partial)
    sender_number = models.CharField(max_length=20, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    payment_state = models.CharField(max_length=30, choices=PAYMENT_STATE_CHOICES, default='awaiting_payment')

    # Delivery charge payment (IMPORTANT for COD)
    delivery_charge_paid = models.BooleanField(default=False)
    delivery_payment_method = models.CharField(
        max_length=20,
        choices=DELIVERY_PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )
    delivery_sender_number = models.CharField(max_length=20, blank=True, null=True)
    delivery_transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    inventory_restored_at = models.DateTimeField(blank=True, null=True)
    coupon_usage_released_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField(blank=True, null=True)

    def set_access_pin(self, raw_pin):
        normalized_pin = (raw_pin or '').strip()
        if not normalized_pin:
            self.access_pin_hash = ''
            return
        self.access_pin_hash = make_password(normalized_pin)

    def check_access_pin(self, raw_pin):
        if not self.access_pin_hash or not raw_pin:
            return False
        return check_password(raw_pin, self.access_pin_hash)

    @property
    def payment_status(self):
        return self.payment_state in {'paid', 'partially_paid'}

    @property
    def requires_payment_follow_up(self):
        return self.payment_state in {'awaiting_payment', 'payment_submitted'}

    @staticmethod
    def _normalize_optional_text(value, *, uppercase=False):
        normalized = (value or '').strip()
        if not normalized:
            return None
        return normalized.upper() if uppercase else normalized

    @classmethod
    def _to_money(cls, amount):
        if amount is None:
            amount = Decimal('0.00')
        return Decimal(str(amount)).quantize(cls.MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

    @classmethod
    def _raise_checkout_error(cls, error_cls, message):
        if error_cls is ValidationError:
            raise ValidationError({'items': message})
        raise error_cls(message)

    @classmethod
    def resolve_checkout_items(cls, raw_items, *, lock_for_update=False, error_cls=ValueError):
        if not isinstance(raw_items, list):
            cls._raise_checkout_error(error_cls, 'Invalid cart data.')

        quantities = {}
        ordered_items = []
        ordered_product_ids = []

        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                cls._raise_checkout_error(error_cls, 'Invalid cart item.')

            try:
                product_id = int(raw_item.get('id'))
                quantity = int(raw_item.get('quantity', 1))
            except (TypeError, ValueError):
                cls._raise_checkout_error(error_cls, 'Invalid cart item.')

            if product_id <= 0 or quantity <= 0:
                cls._raise_checkout_error(error_cls, 'Invalid cart item.')

            selected_color = cls._normalize_optional_text(raw_item.get('color'))
            item_key = (product_id, selected_color.lower())

            if item_key not in quantities:
                ordered_items.append((product_id, selected_color, item_key))
                quantities[item_key] = 0
                if product_id not in ordered_product_ids:
                    ordered_product_ids.append(product_id)

            quantities[item_key] += quantity

        if not ordered_product_ids:
            cls._raise_checkout_error(error_cls, 'Cart is empty.')

        product_queryset = Product.objects.filter(id__in=ordered_product_ids).prefetch_related(
            'color_images__color',
        ).order_by('id')
        if lock_for_update:
            product_queryset = product_queryset.select_for_update()

        products = {product.id: product for product in product_queryset}
        missing_product_ids = [product_id for product_id in ordered_product_ids if product_id not in products]
        if missing_product_ids:
            cls._raise_checkout_error(error_cls, 'Some products are no longer available.')

        resolved_items = []
        subtotal = Decimal('0.00')
        product_quantity_totals = {}

        for product_id, selected_color, item_key in ordered_items:
            product = products[product_id]
            quantity = quantities[item_key]

            available_colors = product.get_available_color_names()
            available_color_lookup = {color.lower(): color for color in available_colors}
            if len(available_colors) > 1:
                if not selected_color:
                    cls._raise_checkout_error(error_cls, f'Please select a color for {product.name}.')
                if selected_color.lower() not in available_color_lookup:
                    cls._raise_checkout_error(error_cls, f'Selected color is not available for {product.name}.')
                selected_color = available_color_lookup[selected_color.lower()]
            elif selected_color:
                if available_colors and selected_color.lower() not in available_color_lookup:
                    cls._raise_checkout_error(error_cls, f'Selected color is not available for {product.name}.')
                selected_color = available_color_lookup.get(selected_color.lower(), selected_color)

            if product.stock < quantity:
                cls._raise_checkout_error(error_cls, f'Not enough stock for {product.name}.')

            product_quantity_totals[product_id] = product_quantity_totals.get(product_id, 0) + quantity
            if product.stock < product_quantity_totals[product_id]:
                cls._raise_checkout_error(error_cls, f'Not enough stock for {product.name}.')

            unit_price = cls._to_money(product.get_final_price())
            line_total = cls._to_money(unit_price * quantity)
            resolved_items.append({
                'product_id': product.id,
                'product': product,
                'product_name': product.name,
                'product_color': selected_color,
                'quantity': quantity,
                'unit_price': unit_price,
                'line_total': line_total,
            })
            subtotal += line_total

        return resolved_items, cls._to_money(subtotal)

    @classmethod
    def shipping_cost_for_state(cls, state):
        normalized_state = (state or '').strip().lower()
        if 'dhaka' in normalized_state:
            return cls.INSIDE_DHAKA_SHIPPING
        return cls.OUTSIDE_DHAKA_SHIPPING

    @classmethod
    def coupon_discount_amount(cls, coupon, subtotal):
        if not coupon:
            return Decimal('0.00')

        if coupon.discount_amount > 0:
            discount_amount = cls._to_money(coupon.discount_amount)
        else:
            discount_amount = cls._to_money(subtotal * Decimal(coupon.discount_percent) / Decimal('100'))

        return min(discount_amount, subtotal)

    @classmethod
    def build_pricing_summary(cls, resolved_items, shipping_state, coupon=None):
        subtotal = cls._to_money(sum(item['line_total'] for item in resolved_items))
        shipping_cost = cls.shipping_cost_for_state(shipping_state) if resolved_items else Decimal('0.00')
        discount_amount = cls.coupon_discount_amount(coupon, subtotal)
        total = cls._to_money(subtotal + shipping_cost - discount_amount)

        return {
            'subtotal': subtotal,
            'shipping_cost': shipping_cost,
            'discount_amount': discount_amount,
            'total': total,
        }

    @classmethod
    def _payment_state_for_method(cls, payment_method, *, delivery_charge_paid):
        if payment_method in cls.MANUAL_PAYMENT_METHODS:
            return 'awaiting_payment'
        if delivery_charge_paid:
            return 'partially_paid'
        return 'awaiting_payment'

    @classmethod
    def _payment_reference_filter(cls, transaction_id=None, delivery_transaction_id=None):
        payment_reference_filter = Q()
        if transaction_id:
            payment_reference_filter |= (
                Q(transaction_id__iexact=transaction_id)
                | Q(delivery_transaction_id__iexact=transaction_id)
            )
        if delivery_transaction_id:
            payment_reference_filter |= (
                Q(transaction_id__iexact=delivery_transaction_id)
                | Q(delivery_transaction_id__iexact=delivery_transaction_id)
            )
        return payment_reference_filter

    @classmethod
    def _create_address(cls, *, user, address_type, address_data, phone, fallback_full_name=None):
        return Address.objects.create(
            user=user,
            address_type=address_type,
            full_name=(address_data.get('full_name') or fallback_full_name or '').strip(),
            phone=phone,
            address_line1=(address_data.get('address_line1') or '').strip(),
            address_line2=(address_data.get('address_line2') or '').strip(),
            city=(address_data.get('city') or '').strip(),
            postal_code=(address_data.get('postal_code') or '').strip(),
            state=(address_data.get('state') or '').strip(),
            country=(address_data.get('country') or 'Bangladesh').strip(),
        )

    @classmethod
    def create_order(
        cls,
        *,
        user=None,
        idempotency_key,
        raw_items,
        personal_info,
        shipping_address_data,
        billing_address_data,
        same_billing_address=True,
        payment_method,
        sender_number=None,
        transaction_id=None,
        delivery_payment_method=None,
        delivery_sender_number=None,
        delivery_transaction_id=None,
        notes='',
        coupon_id=None,
        access_pin='',
    ):
        normalized_idempotency_key = cls._normalize_optional_text(idempotency_key)
        if not normalized_idempotency_key:
            raise ValidationError({'idempotency_key': 'Missing idempotency key.'})

        normalized_payment_method = cls._normalize_optional_text(payment_method)
        normalized_sender_number = cls._normalize_optional_text(sender_number)
        normalized_transaction_id = cls._normalize_optional_text(transaction_id, uppercase=True)
        normalized_delivery_payment_method = cls._normalize_optional_text(delivery_payment_method)
        normalized_delivery_sender_number = cls._normalize_optional_text(delivery_sender_number)
        normalized_delivery_transaction_id = cls._normalize_optional_text(delivery_transaction_id, uppercase=True)
        phone = (personal_info.get('phone') or '').strip()
        shipping_full_name = (shipping_address_data.get('full_name') or personal_info.get('full_name') or '').strip()
        billing_full_name = (billing_address_data.get('full_name') or personal_info.get('full_name') or '').strip()

        required_values = [
            ((personal_info.get('full_name') or '').strip(), 'full_name'),
            ((personal_info.get('email') or '').strip(), 'email'),
            (phone, 'phone'),
            (shipping_full_name, 'shipping_full_name'),
            ((shipping_address_data.get('address_line1') or '').strip(), 'shipping_address_line1'),
            ((shipping_address_data.get('address_line2') or '').strip(), 'shipping_address_line2'),
            ((shipping_address_data.get('city') or '').strip(), 'shipping_city'),
            ((shipping_address_data.get('postal_code') or '').strip(), 'shipping_postal_code'),
            ((shipping_address_data.get('state') or '').strip(), 'shipping_state'),
            ((shipping_address_data.get('country') or 'Bangladesh').strip(), 'shipping_country'),
        ]
        if not same_billing_address:
            required_values.extend([
                (billing_full_name, 'billing_full_name'),
                ((billing_address_data.get('address_line1') or '').strip(), 'billing_address_line1'),
                ((billing_address_data.get('address_line2') or '').strip(), 'billing_address_line2'),
                ((billing_address_data.get('city') or '').strip(), 'billing_city'),
                ((billing_address_data.get('postal_code') or '').strip(), 'billing_postal_code'),
                ((billing_address_data.get('state') or '').strip(), 'billing_state'),
                ((billing_address_data.get('country') or 'Bangladesh').strip(), 'billing_country'),
            ])

        for value, field_name in required_values:
            if not value:
                raise ValidationError({field_name: 'This field is required.'})

        with transaction.atomic():
            existing_order = cls.objects.select_for_update().filter(idempotency_key=normalized_idempotency_key).first()
            if existing_order:
                return existing_order, False

            resolved_items, subtotal = cls.resolve_checkout_items(
                raw_items,
                lock_for_update=True,
                error_cls=ValidationError,
            )

            payment_reference_filter = cls._payment_reference_filter(
                normalized_transaction_id,
                normalized_delivery_transaction_id,
            )
            if payment_reference_filter.children and cls.objects.select_for_update().filter(payment_reference_filter).exists():
                raise ValidationError({'transaction_id': 'This transaction ID is already linked to another order.'})

            coupon = None
            if coupon_id:
                coupon = Coupon.objects.select_for_update().filter(pk=coupon_id, is_active=True).first()
                is_valid, coupon_message = coupon.validate_for_subtotal(subtotal) if coupon else (False, 'Invalid coupon code.')
                if not is_valid:
                    raise ValidationError({'coupon': coupon_message or 'This coupon is no longer available.'})

            delivery_charge_paid = bool(
                normalized_delivery_payment_method
                or normalized_delivery_sender_number
                or normalized_delivery_transaction_id
            )
            payment_state = cls._payment_state_for_method(
                normalized_payment_method,
                delivery_charge_paid=delivery_charge_paid,
            )
            shipping_state = (shipping_address_data.get('state') or '').strip()
            pricing = cls.build_pricing_summary(resolved_items, shipping_state, coupon)

            shipping_address = cls._create_address(
                user=user,
                address_type='shipping',
                address_data=shipping_address_data,
                phone=phone,
                fallback_full_name=shipping_full_name,
            )
            if same_billing_address:
                billing_address = shipping_address
            else:
                billing_address = cls._create_address(
                    user=user,
                    address_type='billing',
                    address_data=billing_address_data,
                    phone=phone,
                    fallback_full_name=billing_full_name,
                )

            order = cls(
                user=user,
                coupon=coupon,
                idempotency_key=normalized_idempotency_key,
                full_name=(personal_info.get('full_name') or '').strip(),
                email=(personal_info.get('email') or '').strip(),
                phone=phone,
                shipping_address=shipping_address,
                billing_address=billing_address,
                total_price=pricing['total'],
                original_price=pricing['subtotal'],
                shipping_cost=pricing['shipping_cost'],
                discount_amount=pricing['discount_amount'],
                order_status='pending',
                payment_method=normalized_payment_method,
                sender_number=normalized_sender_number if normalized_payment_method in cls.MANUAL_PAYMENT_METHODS else None,
                transaction_id=normalized_transaction_id if normalized_payment_method in cls.MANUAL_PAYMENT_METHODS else None,
                payment_state=payment_state,
                delivery_charge_paid=delivery_charge_paid if normalized_payment_method == 'cash_on_delivery' else False,
                delivery_payment_method=normalized_delivery_payment_method if normalized_payment_method == 'cash_on_delivery' else None,
                delivery_sender_number=normalized_delivery_sender_number if normalized_payment_method == 'cash_on_delivery' else None,
                delivery_transaction_id=normalized_delivery_transaction_id if normalized_payment_method == 'cash_on_delivery' else None,
                notes=(notes or '').strip(),
            )
            order.set_access_pin(access_pin)
            order.save()

            for item in resolved_items:
                updated = Product.objects.filter(
                    pk=item['product'].pk,
                    stock__gte=item['quantity'],
                ).update(stock=F('stock') - item['quantity'])
                if not updated:
                    raise ValidationError({'items': f'Not enough stock for {item["product_name"]}.'})

                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_name=item['product_name'],
                    product_color=item['product_color'],
                    product_price=item['unit_price'],
                    quantity=item['quantity'],
                )

            if coupon:
                coupon.consume_locked()

            return order, True

    def clean(self):
        super().clean()

        self.idempotency_key = self._normalize_optional_text(self.idempotency_key)
        self.sender_number = self._normalize_optional_text(self.sender_number)
        self.transaction_id = self._normalize_optional_text(
            self.transaction_id,
            uppercase=True
        )

        self.delivery_payment_method = self._normalize_optional_text(
            self.delivery_payment_method
        )
        self.delivery_sender_number = self._normalize_optional_text(
            self.delivery_sender_number
        )
        self.delivery_transaction_id = self._normalize_optional_text(
            self.delivery_transaction_id,
            uppercase=True
        )

        errors = {}

        manual_payment = self.payment_method in self.MANUAL_PAYMENT_METHODS
        cash_on_delivery = self.payment_method == 'cash_on_delivery'

        # -------- MANUAL PAYMENT (bKash/Nagad) --------

        if manual_payment:

            # delivery fields never belong here
            if any([
                self.delivery_charge_paid,
                self.delivery_payment_method,
                self.delivery_sender_number,
                self.delivery_transaction_id
            ]):
                errors['delivery_payment_method'] = (
                    'Delivery charge fields only belong to COD.'
                )

            # sender + trx become OPTIONAL until admin verifies
            if self.payment_state == 'paid':
                if not self.sender_number:
                    errors['sender_number'] = (
                        'Sender number required before marking paid.'
                    )

                if not self.transaction_id:
                    errors['transaction_id'] = (
                        'Transaction ID required before marking paid.'
                    )

        # -------- COD --------

        elif cash_on_delivery:

            if self.sender_number:
                errors['sender_number'] = (
                    'Sender number not used for COD.'
                )

            if self.transaction_id:
                errors['transaction_id'] = (
                    'Transaction ID not used for COD.'
                )

            delivery_details_supplied = any([
                self.delivery_payment_method,
                self.delivery_sender_number,
                self.delivery_transaction_id,
            ])

            if delivery_details_supplied:

                # automatically mark paid
                self.delivery_charge_paid = True

                if self.delivery_payment_method not in {
                    'bkash',
                    'nagad'
                }:
                    errors['delivery_payment_method'] = (
                        'Select bKash or Nagad.'
                    )

                if not self.delivery_sender_number:
                    errors['delivery_sender_number'] = (
                        'Sender number required.'
                    )

                if not self.delivery_transaction_id:
                    errors['delivery_transaction_id'] = (
                        'Transaction ID required.'
                    )

            else:
                self.delivery_charge_paid = False

            if (
                self.payment_state == 'partially_paid'
                and not self.delivery_charge_paid
            ):
                errors['payment_state'] = (
                    'COD can only become partially paid after delivery charge payment.'
                )

        else:
            errors['payment_method'] = 'Invalid payment method.'

        # delivered order must stay paid

        if (
            self.order_status == 'delivered'
            and self.payment_state != 'paid'
        ):
            errors['payment_state'] = (
                'Delivered orders must be paid.'
            )

        # refunds

        if (
            self.order_status == 'refunded'
            and self.payment_state != 'refunded'
        ):
            errors['payment_state'] = (
                'Refunded orders must also be refunded.'
            )

        if (
            self.payment_state == 'refunded'
            and self.order_status not in {
                'cancelled',
                'refunded'
            }
        ):
            errors['order_status'] = (
                'Refunded payment requires cancelled/refunded order.'
            )

        # duplicate transaction checks

        duplicate_reference_filters = Q()

        if self.transaction_id:
            duplicate_reference_filters |= (
                Q(transaction_id__iexact=self.transaction_id)
                |
                Q(delivery_transaction_id__iexact=self.transaction_id)
            )

        if self.delivery_transaction_id:
            duplicate_reference_filters |= (
                Q(transaction_id__iexact=self.delivery_transaction_id)
                |
                Q(delivery_transaction_id__iexact=self.delivery_transaction_id)
            )

        if duplicate_reference_filters.children:

            duplicates = (
                Order.objects
                .exclude(pk=self.pk)
                .filter(duplicate_reference_filters)
            )

            if (
                self.transaction_id
                and duplicates.filter(
                    Q(transaction_id__iexact=self.transaction_id)
                    |
                    Q(delivery_transaction_id__iexact=self.transaction_id)
                ).exists()
            ):
                errors['transaction_id'] = (
                    'Transaction ID already used.'
                )

            if (
                self.delivery_transaction_id
                and duplicates.filter(
                    Q(transaction_id__iexact=self.delivery_transaction_id)
                    |
                    Q(delivery_transaction_id__iexact=self.delivery_transaction_id)
                ).exists()
            ):
                errors['delivery_transaction_id'] = (
                    'Transaction ID already used.'
                )

        if errors:
            raise ValidationError(errors)
        
    def save(self, *args, **kwargs):
        if not self.order_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.order_number = f"ORD{timestamp}{random_suffix}"
        
        state_mutation_allowed = getattr(self, '_allow_state_mutation', False)
        if self.pk and not state_mutation_allowed:
            previous = type(self).objects.filter(pk=self.pk).values(
                'order_status',
                'payment_state',
                'delivery_charge_paid',
                'inventory_restored_at',
                'coupon_usage_released_at',
            ).first()
            if previous and (
                previous['order_status'] != self.order_status
                or previous['payment_state'] != self.payment_state
                or previous['delivery_charge_paid'] != self.delivery_charge_paid
                or previous['inventory_restored_at'] != self.inventory_restored_at
                or previous['coupon_usage_released_at'] != self.coupon_usage_released_at
            ):
                raise ValidationError('Use the order transition helpers to change lifecycle or payment state.')

        self.full_clean()
        return super().save(*args, **kwargs)

    def _save_with_state_mutation(self, *, update_fields=None):
        if update_fields is not None:
            update_fields = list(dict.fromkeys([*update_fields, 'updated_at']))

        self._allow_state_mutation = True
        try:
            self.save(update_fields=update_fields)
        finally:
            self._allow_state_mutation = False

    def _restore_inventory_locked(self):
        if self.inventory_restored_at:
            return False

        product_quantities = {
            row['product']: row['total_quantity']
            for row in self.items.filter(product__isnull=False).values('product').annotate(total_quantity=Sum('quantity'))
        }

        product_ids = sorted(product_quantities.keys())
        if product_ids:
            list(
                Product.objects.select_for_update()
                .filter(id__in=product_ids)
                .order_by('id')
                .values_list('id', flat=True)
            )
            for product_id in product_ids:
                Product.objects.filter(pk=product_id).update(stock=F('stock') + product_quantities[product_id])

        self.inventory_restored_at = timezone.now()
        return True

    def _release_coupon_usage_locked(self):
        if not self.coupon_id or self.coupon_usage_released_at:
            return False

        coupon = Coupon.objects.select_for_update().filter(pk=self.coupon_id).first()
        if coupon:
            coupon.release_locked()

        self.coupon_usage_released_at = timezone.now()
        return True

    def can_transition_order_status(self, new_status):
        return new_status in self.ORDER_STATUS_TRANSITIONS.get(self.order_status, set())

    def can_transition_payment_state(self, new_state):
        return new_state in self.PAYMENT_STATE_TRANSITIONS.get(self.payment_state, set())

    def _transition_order_status_locked(self, new_status):
        normalized_status = (new_status or '').strip().lower()
        if normalized_status == self.order_status:
            return False

        if not self.can_transition_order_status(normalized_status):
            raise ValidationError({
                'order_status': f'Cannot change order status from {self.get_order_status_display()} to {normalized_status}.'
            })

        update_fields = ['order_status']

        if normalized_status == 'delivered':
            if self.payment_method in self.MANUAL_PAYMENT_METHODS and self.payment_state != 'paid':
                raise ValidationError({'payment_state': 'Manual payment orders must be marked paid before they are delivered.'})
            if self.payment_method == 'cash_on_delivery' and self.payment_state != 'paid':
                self.payment_state = 'paid'
                update_fields.append('payment_state')

        if normalized_status in self.TERMINAL_STATUSES:
            if self._restore_inventory_locked():
                update_fields.append('inventory_restored_at')
            if self._release_coupon_usage_locked():
                update_fields.append('coupon_usage_released_at')

        if normalized_status == 'refunded' and self.payment_state != 'refunded':
            self.payment_state = 'refunded'
            update_fields.append('payment_state')

        self.order_status = normalized_status
        self._save_with_state_mutation(update_fields=update_fields)
        return True

    def transition_order_status(self, new_status):
        if not self.pk:
            raise ValidationError('Order must be saved before it can change status.')

        with transaction.atomic():
            locked_order = type(self).objects.select_for_update().prefetch_related('items').get(pk=self.pk)
            changed = locked_order._transition_order_status_locked(new_status)

        self.refresh_from_db()
        return changed

    def _transition_payment_state_locked(self, new_state):
        normalized_state = (new_state or '').strip().lower()
        if normalized_state == self.payment_state:
            return False

        if not self.can_transition_payment_state(normalized_state):
            raise ValidationError({
                'payment_state': f'Cannot change payment state from {self.get_payment_state_display()} to {normalized_state}.'
            })

        if normalized_state == 'partially_paid':
            if self.payment_method != 'cash_on_delivery' or not self.delivery_charge_paid:
                raise ValidationError({'payment_state': 'Only COD orders with a paid delivery charge can be marked partially paid.'})

        if normalized_state == 'paid' and self.payment_method in self.MANUAL_PAYMENT_METHODS:
            if not self.sender_number or not self.transaction_id:
                raise ValidationError({'payment_state': 'Manual payments must keep both sender number and transaction ID before they are marked paid.'})

        if normalized_state == 'refunded':
            return self._transition_order_status_locked('refunded')

        if self.order_status == 'delivered' and normalized_state != 'paid':
            raise ValidationError({'payment_state': 'Delivered orders must remain marked as paid.'})

        self.payment_state = normalized_state
        self._save_with_state_mutation(update_fields=['payment_state'])
        return True

    def transition_payment_state(self, new_state):
        if not self.pk:
            raise ValidationError('Order must be saved before its payment state can change.')

        with transaction.atomic():
            locked_order = type(self).objects.select_for_update().get(pk=self.pk)
            changed = locked_order._transition_payment_state_locked(new_state)

        self.refresh_from_db()
        return changed

    def _mark_delivery_charge_paid_locked(self):
        if self.payment_method != 'cash_on_delivery':
            raise ValidationError({'delivery_charge_paid': 'Only cash on delivery orders can record a separate delivery charge payment.'})
        if self.delivery_charge_paid:
            return False
        if not self.delivery_payment_method:
            raise ValidationError({'delivery_payment_method': 'Select the delivery charge payment method first.'})
        if not self.delivery_sender_number:
            raise ValidationError({'delivery_sender_number': 'Sender number is required for online delivery charge payments.'})
        if not self.delivery_transaction_id:
            raise ValidationError({'delivery_transaction_id': 'Transaction ID is required for online delivery charge payments.'})

        update_fields = ['delivery_charge_paid']
        if self.payment_state in {'awaiting_payment', 'failed'}:
            self.payment_state = 'partially_paid'
            update_fields.append('payment_state')

        self.delivery_charge_paid = True
        self._save_with_state_mutation(update_fields=update_fields)
        return True

    def mark_delivery_charge_paid(self):
        if not self.pk:
            raise ValidationError('Order must be saved before delivery charge can be recorded.')

        with transaction.atomic():
            locked_order = type(self).objects.select_for_update().get(pk=self.pk)
            changed = locked_order._mark_delivery_charge_paid_locked()

        self.refresh_from_db()
        return changed

    def __str__(self):
        return f"Order {self.id}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['order_status']),
            models.Index(fields=['payment_state']),
            models.Index(fields=['order_status', 'created_at']),
            models.Index(fields=['payment_state', 'created_at']),
        ]

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, related_name='order_items')
    product_name = models.CharField(max_length=255)
    product_color = models.CharField(max_length=120, blank=True, default='')
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    class Meta:
        ordering = ['id']

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.PositiveIntegerField(null=True, blank=True, help_text="Fixed discount amount")
    discount_percent = models.PositiveIntegerField(null=True, blank=True, help_text="Percentage discount")
    minimum_order_value = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=0, help_text="0 means unlimited usage")
    used_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        if self.discount_amount:
            return f"{self.code} (Tk {self.discount_amount} off)"
        return f"{self.code} ({self.discount_percent}% off)"

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.valid_from or not self.valid_to:
            return False
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            (self.usage_limit == 0 or self.used_count < self.usage_limit)
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.discount_amount not in [None, 0] and self.discount_percent not in [None, 0]:
            errors['discount_percent'] = 'Use either fixed discount or percentage discount, not both.'
        if self.discount_amount in [None, 0] and self.discount_percent in [None, 0]:
            errors['discount_amount'] = 'Set either a fixed discount or a percentage discount.'
        if self.discount_percent is not None and self.discount_percent > 100:
            errors['discount_percent'] = 'Discount percentage cannot exceed 100.'
        if self.valid_from and self.valid_to:
            if self.valid_to <= self.valid_from:
                errors['valid_to'] = 'Coupon expiry must be after the start time.'
        if errors:
            raise ValidationError(errors)

    def validate_for_subtotal(self, subtotal):
        if not self.is_active:
            return False, 'This coupon is no longer active.'
        if not self.valid_from or not self.valid_to:
            return False, 'Coupon validity dates are missing.'
        now = timezone.now()
        if not (self.valid_from <= now <= self.valid_to):
            return False, 'This coupon is no longer valid.'
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, 'This coupon has reached its usage limit.'
        if subtotal is not None:
            minimum_order_value = subtotal.__class__(str(self.minimum_order_value))
            if minimum_order_value and subtotal < minimum_order_value:
                return False, f'Minimum order amount for this coupon is Tk {minimum_order_value:.2f}.'
        return True, ''

    def consume_locked(self):
        if self.usage_limit and self.used_count >= self.usage_limit:
            raise ValidationError({'code': 'This coupon has already reached its usage limit.'})
        Coupon.objects.filter(pk=self.pk).update(used_count=F('used_count') + 1)
        self.refresh_from_db(fields=['used_count'])

    def release_locked(self):
        Coupon.objects.filter(pk=self.pk, used_count__gt=0).update(used_count=F('used_count') - 1)
        self.refresh_from_db(fields=['used_count'])


class AdminAlert(models.Model):
    """
    Model for tracking system alerts and notifications
    - Low stock alerts
    - High order volume alerts
    - Failed payment alerts
    """
    ALERT_TYPES = (
        ('low_stock', 'Low Stock Alert'),
        ('high_orders', 'High Order Volume'),
        ('failed_payment', 'Failed Payment'),
        ('system', 'System Alert'),
    )
    
    SEVERITY_LEVELS = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    )
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='warning')
    title = models.CharField(max_length=255)
    message = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    is_read = models.BooleanField(default=False)
    read_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='read_alerts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.title}"
    
    class Meta:
        ordering = ['-created_at', '-severity']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_read']),
            models.Index(fields=['severity']),
        ]


class PromoBanner(models.Model):
    title_1 = models.CharField(max_length=100)
    title_2 = models.CharField(max_length=100)
    description = models.TextField(max_length=300)
    image = models.ImageField(upload_to='promo_banners/')
    is_active = models.BooleanField(default=False)

    def clean(self):
        if self.is_active:
            existing = PromoBanner.objects.filter(
                is_active=True
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    "Only one PromoBanner can be active."
                )

    def save(self, *args, **kwargs):
        self.full_clean()   # runs clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title_1} ({'Active' if self.is_active else 'Inactive'})"
