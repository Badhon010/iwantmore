from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name
class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.PositiveIntegerField() 
    image = models.ImageField(upload_to='product_images/')
    stock = models.PositiveIntegerField(default=0)  # Track stock levels
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, related_name="products")  # Link to Tag model
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)  # Auto-generate slug from name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
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