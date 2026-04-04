from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.urls import reverse
import json

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
    discount_price = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='product_images/')
    stock = models.PositiveIntegerField(default=0)  
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField('Tag', related_name="products")  
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, editable=False, related_name='products')
    subcategory = models.ForeignKey('SubCategory', on_delete=models.SET_NULL, null=True, related_name='products')
    is_featured = models.BooleanField(default=False)
    feature_reason = models.ForeignKey('FeatureReason', on_delete=models.SET_NULL, null=True, blank=True, related_name='featured_products')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
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

    def update_stock(self, quantity_change):
        """
        Update product stock level
        
        Args:
            quantity_change: Integer indicating change in quantity (positive for increase, negative for decrease)
        
        Returns:
            Boolean: True if update was successful, False if there's not enough stock
        """
        if self.stock + quantity_change < 0:
            return False
            
        self.stock += quantity_change
        self.save(update_fields=['stock'])
        return True

class MoreImages(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="more_images")  # ForeignKey ব্যবহার করা হয়েছে
    image = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"Image for {self.product.name}"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name} - {self.rating}★"
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

    DELIVERY_PAYMENT_METHOD_CHOICES = (
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    idempotency_key = models.CharField(max_length=64, unique=True, blank=True, null=True)

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
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    payment_status = models.BooleanField(default=False)

    # Delivery charge payment (IMPORTANT for COD)
    delivery_charge_paid = models.BooleanField(default=False)
    delivery_payment_method = models.CharField(
        max_length=20,
        choices=DELIVERY_PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )
    delivery_transaction_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.id}"

    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, related_name='order_items')
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    class Meta:
        ordering = ['id']

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.PositiveIntegerField(default=0)  # Fixed amount discount
    discount_percent = models.PositiveIntegerField(default=0)  # Percentage discount
    minimum_order_value = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=0)  # 0 means unlimited
    used_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        if self.discount_amount > 0:
            return f"{self.code} (৳{self.discount_amount} off)"
        return f"{self.code} ({self.discount_percent}% off)"
    
    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and 
            self.valid_from <= now <= self.valid_to and
            (self.usage_limit == 0 or self.used_count < self.usage_limit)
        )


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
