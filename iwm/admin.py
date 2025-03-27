from django.contrib import admin
from .models import Product, Review, Tag, MoreImages, NewsletterSubscriber, Category, SubCategory, FeatureReason, Order, OrderItem, Address, Coupon, Color, Size, Brand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django import forms
from django.conf import settings

# Customize the Django Admin Panel Titles
admin.site.site_header = "I Want More Admin"
admin.site.site_title = "I Want More Admin Panel"
admin.site.index_title = "Welcome to I Want More Admin"

# Register Category and SubCategory models
class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubCategoryInline]

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug')
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(FeatureReason)
class FeatureReasonAdmin(admin.ModelAdmin):
    list_display = ('Reason',)

# Register Review model
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username')

class MoreImagesInline(admin.TabularInline):
    model = MoreImages
    extra = 1  # নতুন ইমেজ আপলোড করার জন্য ফাঁকা ফিল্ড দেখাবে

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)


# Register Product model with custom admin - FIXED ORDER
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("admin/custom.css",)}
        js = ("admin/custom.js",)

    list_display = ('name', 'price', 'discount_price', 'subcategory', 'is_featured', 'created_at', 'get_color', 'get_size', 'get_brand')
    search_fields = ('name', 'description')
    list_filter = ('price', 'discount_price', 'tags', 'subcategory', 'is_featured','color', 'size', 'brand')
    filter_horizontal = ('tags',)
    inlines = [MoreImagesInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'price', 'discount_price', 'image', 'stock')
        }),
        ('Categorization', {
            'fields': ('subcategory', 'tags')  # এখানে 'category' বাদ দেওয়া হয়েছে
        }),
        ('Product Attributes', {
        'fields': ('color', 'size', 'brand')  # Add your ManyToMany fields here.
        }),
        ('Featured', {
            'fields': ('is_featured', 'feature_reason')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if obj.subcategory:
            obj.category = obj.subcategory.category  # Admin panel-এও Category অটো সেট হবে
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subcategory":
            kwargs["queryset"] = SubCategory.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_color(self, obj):
        return obj.color.name if obj.color else "-"
    get_color.short_description = "Color"

    def get_size(self, obj):
        return obj.size.name if obj.size else "-"
    get_size.short_description = "Size"

    def get_brand(self, obj):
        return obj.brand.name if obj.brand else "-"
    get_brand.short_description = "Brand"

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(MoreImages)
class MoreImagesAdmin(admin.ModelAdmin):
    list_display = ('product',)
    list_filter = ('product',)


# Email sending form for newsletter subscribers
class EmailForm(forms.Form):
    subject = forms.CharField(max_length=100, required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)
    send_to_inactive = forms.BooleanField(required=False, initial=False,
                                         help_text="Send to inactive subscribers as well")
    send_html = forms.BooleanField(required=False, initial=True,
                                  help_text="Send as HTML email (recommended)")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active', 'source')
    list_filter = ('is_active', 'subscribed_at', 'source')
    search_fields = ('email', 'source')
    date_hierarchy = 'subscribed_at'
    actions = ['mark_active', 'mark_inactive', 'send_email_to_selected']
    
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscribers marked as active.')
    mark_active.short_description = "Mark selected subscribers as active"
    
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscribers marked as inactive.')
    mark_inactive.short_description = "Mark selected subscribers as inactive"
    
    def send_email_to_selected(self, request, queryset):
        # Get the IDs of the selected subscribers
        selected = queryset.values_list('pk', flat=True)
        
        # Store the selected IDs in the session for later use
        request.session['selected_subscribers'] = list(map(str, selected))
        
        # Redirect to the custom email form view
        return HttpResponseRedirect("../send-newsletter-email/")
    send_email_to_selected.short_description = "Send email to selected subscribers"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-newsletter-email/', self.admin_site.admin_view(self.send_newsletter_email_view), 
                 name='send-newsletter-email'),
            path('send-newsletter-to-all/', self.admin_site.admin_view(self.send_newsletter_to_all_view), 
                 name='send-newsletter-to-all'),
        ]
        return custom_urls + urls
    
    def send_newsletter_email_view(self, request):
        # Get the selected subscribers from the session
        selected_ids = request.session.get('selected_subscribers', [])
        subscribers = NewsletterSubscriber.objects.filter(pk__in=selected_ids)
        
        if request.method == 'POST':
            form = EmailForm(request.POST)
            if form.is_valid():
                subject = form.cleaned_data['subject']
                message = form.cleaned_data['message']
                send_html = form.cleaned_data['send_html']
                send_to_inactive = form.cleaned_data['send_to_inactive']
                
                if not send_to_inactive:
                    subscribers = subscribers.filter(is_active=True)
                
                self.send_emails(request, subscribers, subject, message, send_html)
                
                # Clear the session
                if 'selected_subscribers' in request.session:
                    del request.session['selected_subscribers']
                
                return HttpResponseRedirect("../../")
        else:
            form = EmailForm()
        
        context = {
            'form': form,
            'subscribers': subscribers,
            'opts': self.model._meta,
            'title': 'Send Email to Selected Subscribers',
        }
        return TemplateResponse(request, 'admin/send_newsletter_email.html', context)
    
    def send_newsletter_to_all_view(self, request):
        # Get all active subscribers
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)
        
        if request.method == 'POST':
            form = EmailForm(request.POST)
            if form.is_valid():
                subject = form.cleaned_data['subject']
                message = form.cleaned_data['message']
                send_html = form.cleaned_data['send_html']
                send_to_inactive = form.cleaned_data['send_to_inactive']
                
                if send_to_inactive:
                    subscribers = NewsletterSubscriber.objects.all()
                
                self.send_emails(request, subscribers, subject, message, send_html)
                
                return HttpResponseRedirect("../../")
        else:
            form = EmailForm()
        
        context = {
            'form': form,
            'subscribers': subscribers,
            'opts': self.model._meta,
            'title': 'Send Email to All Subscribers',
        }
        return TemplateResponse(request, 'admin/send_newsletter_email.html', context)
    
    def send_emails(self, request, subscribers, subject, message, send_html):
        # Prepare the email
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [subscriber.email for subscriber in subscribers]
        
        if not recipient_list:
            self.message_user(request, "No active subscribers to send emails to.")
            return
        
        try:
            if send_html:
                # Send HTML email
                for email in recipient_list:
                    mail = EmailMultiAlternatives(
                        subject=subject,
                        body=message,
                        from_email=from_email,
                        to=[email],
                    )
                    # Convert message to HTML
                    html_message = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                            .container {{ padding: 20px; max-width: 600px; margin: 0 auto; }}
                            .header {{ background-color: #ff6f91; color: white; padding: 10px 20px; text-align: center; }}
                            .content {{ background-color: #f7f7f7; padding: 20px; }}
                            .footer {{ font-size: 12px; color: #777; text-align: center; margin-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h2>I Want More Newsletter</h2>
                            </div>
                            <div class="content">
                                {message.replace('\\n', '<br>')}
                            </div>
                            <div class="footer">
                                <p>You received this email because you subscribed to I Want More newsletter.</p>
                                <p>© {{% now "Y" %}} I Want More. All rights reserved.</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    mail.attach_alternative(html_message, "text/html")
                    mail.send()
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=recipient_list,
                    fail_silently=False,
                )
            
            self.message_user(request, f"Successfully sent {len(recipient_list)} emails.")
        except Exception as e:
            self.message_user(request, f"Error sending emails: {str(e)}", level='ERROR')
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_send_to_all'] = True
        return super().changelist_view(request, extra_context=extra_context)

# Admin for Order Management

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_price', 'quantity']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'get_customer_name', 'total_price', 'order_status', 'payment_status', 'created_at']
    list_filter = ['order_status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['id', 'user__username', 'shipping_address__full_name', 'shipping_address__phone']
    readonly_fields = ['user', 'full_name', 'email', 'phone', 'shipping_address', 'billing_address', 
                      'payment_method', 'transaction_id', 'original_price', 'shipping_cost', 
                      'discount_amount', 'total_price', 'created_at', 'updated_at']
    fieldsets = [
        ('Order Information', {
            'fields': ['order_status', 'user', 'full_name', 'email', 'phone', 'created_at', 'updated_at']
        }),
        ('Customer Information', {
            'fields': ['shipping_address', 'billing_address']
        }),
        ('Payment Information', {
            'fields': ['payment_method', 'payment_status', 'transaction_id']
        }),
        ('Financial Details', {
            'fields': ['original_price', 'shipping_cost', 'discount_amount', 'total_price']
        }),
        ('Shipping Details', {
            'fields': ['tracking_number', 'estimated_delivery']
        }),
        ('Additional Information', {
            'fields': ['notes']
        }),
    ]
    inlines = [OrderItemInline]
    
    def get_customer_name(self, obj):
        if obj.shipping_address:
            return obj.shipping_address.full_name
        return "N/A"
    get_customer_name.short_description = "Customer"
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of orders for data integrity
        return False
    
    def has_add_permission(self, request):
        # Orders should be created through the website, not the admin
        return False

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'product_price', 'quantity', 'get_total')
    list_filter = ('order__order_status',)
    search_fields = ('product_name', 'order__id')
    
    def get_total(self, obj):
        return f"৳{obj.product_price * obj.quantity}"
    get_total.short_description = "Total"

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'city', 'address_type', 'user', 'created_at']
    list_filter = ['address_type', 'city', 'created_at']
    search_fields = ['full_name', 'address_line1', 'city', 'phone']
    readonly_fields = ['created_at']
    fieldsets = [
        ('Personal Information', {
            'fields': ['user', 'full_name', 'phone']
        }),
        ('Address Information', {
            'fields': ['address_line1', 'address_line2', 'city', 'postal_code', 'state', 'country', 'address_type', 'default']
        }),
        ('System Information', {
            'fields': ['created_at']
        }),
    ]

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_display', 'minimum_order_value', 'is_active', 'valid_from', 'valid_to', 'usage_limit', 'used_count')
    list_filter = ('is_active', 'valid_from', 'valid_to')
    search_fields = ('code',)
    readonly_fields = ('used_count',)
    fieldsets = (
        ("Coupon Information", {
            'fields': ('code', 'is_active')
        }),
        ("Discount Details", {
            'fields': ('discount_amount', 'discount_percent', 'minimum_order_value')
        }),
        ("Validity", {
            'fields': ('valid_from', 'valid_to', 'usage_limit', 'used_count')
        }),
    )
    
    def discount_display(self, obj):
        if obj.discount_amount > 0:
            return f"৳{obj.discount_amount}"
        return f"{obj.discount_percent}%"
    discount_display.short_description = "Discount"
