from django.urls.resolvers import URLPattern, URLResolver
from typing import Any
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.db.models import Sum, Count, Q, F, DecimalField
from django.utils import timezone
from django import forms
from django.conf import settings
from datetime import timedelta, datetime
import json
import csv

from import_export import resources
from import_export.admin import ExportActionMixin

import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    Product, Review, Tag, MoreImages, NewsletterSubscriber,
    Category, SubCategory, FeatureReason, Order, OrderItem,
    Address, Coupon, Color, Size, Brand, AdminAlert
)


# ========================
# EXPORT RESOURCES
# ========================

class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'stock', 'category', 'created_at')


class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = ('id', 'full_name', 'email', 'phone', 'total_price', 'payment_status', 'order_status', 'created_at')


class NewsletterSubscriberResource(resources.ModelResource):
    class Meta:
        model = NewsletterSubscriber
        fields = ('id', 'email', 'source', 'is_active', 'subscribed_at')


# ========================
# AUTOMATED ALERTS
# ========================

def check_and_create_alerts():
    """Check all alert conditions and create necessary alerts"""
    # Low stock
    low_stock = Product.objects.filter(stock__lt=10, stock__gt=0)
    for product in low_stock:
        if not AdminAlert.objects.filter(
            product=product,
            alert_type='low_stock',
            is_read=False,
            created_at__date=timezone.now().date()
        ).exists():
            AdminAlert.objects.create(
                alert_type='low_stock',
                severity='warning',
                title=f"Low Stock: {product.name}",
                message=f"Product '{product.name}' has only {product.stock} units left.",
                product=product
            )
    
    # High orders
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today).count()
    if today_orders > 20:
        if not AdminAlert.objects.filter(
            alert_type='high_orders',
            is_read=False,
            created_at__date=today
        ).exists():
            AdminAlert.objects.create(
                alert_type='high_orders',
                severity='info',
                title="High Order Volume Detected",
                message=f"Today has {today_orders} orders - significantly higher than usual."
            )
    
    # Failed payments (pending > 24 hours)
    threshold = timezone.now() - timedelta(hours=24)
    failed_payments = Order.objects.filter(
        payment_status=False,
        order_status__in=['pending', 'processing'],
        created_at__lt=threshold
    )
    for order in failed_payments:
        if not AdminAlert.objects.filter(
            order=order,
            alert_type='failed_payment',
            is_read=False
        ).exists():
            AdminAlert.objects.create(
                alert_type='failed_payment',
                severity='critical',
                title=f"Unpaid Order: #{order.id}",
                message=f"Order #{order.id} from {order.full_name} hasn't been paid for over 24 hours.",
                order=order
            )


# ========================
# CUSTOM ADMIN SITE WITH CHARTS
# ========================

class IWMAdminSite(admin.AdminSite):
    site_header = "I Want More Admin"
    site_title = "I Want More Admin Panel"
    index_title = "Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('revenue-chart/', self.admin_view(self.revenue_chart_view), name='revenue-chart'),
            path('analytics/', self.admin_view(self.analytics_view), name='analytics'),
            path('alerts/', self.admin_view(self.alerts_view), name='alerts'),
        ]
        return custom_urls + urls
    
    def revenue_chart_view(self, request):
        """Generate interactive revenue trend chart"""
        days = 30
        daily_data = []
        
        for i in range(days, 0, -1):
            date = timezone.now().date() - timedelta(days=i)
            revenue = Order.objects.filter(
                created_at__date=date,
                payment_status=True
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0
            daily_data.append({'date': str(date), 'revenue': float(revenue)})
        
        dates = [d['date'] for d in daily_data]
        revenues = [d['revenue'] for d in daily_data]
        
        fig = go.Figure(data=go.Scatter(
            x=dates, y=revenues,
            mode='lines+markers',
            name='Daily Revenue',
            line=dict(color='#ff6f91', width=3),
            marker=dict(size=8, color='#ff6f91')
        ))
        
        fig.update_layout(
            title="30-Day Revenue Trend",
            xaxis_title="Date",
            yaxis_title="Revenue (৳)",
            template="plotly_dark",
            hovermode='x unified',
            height=500
        )
        
        chart_html = plot(fig, output_type='div', include_plotlyjs='cdn')
        
        return TemplateResponse(request, 'admin/revenue_chart.html', {
            'chart': chart_html,
            'title': 'Revenue Trend Chart'
        })
    
    def analytics_view(self, request):
        """Comprehensive analytics dashboard"""
        check_and_create_alerts()
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Order statistics
        today_orders = Order.objects.filter(created_at__date=today)
        week_orders = Order.objects.filter(created_at__date__gte=week_ago)
        month_orders = Order.objects.filter(created_at__date__gte=month_ago)
        
        today_revenue = today_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        week_revenue = week_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        month_revenue = month_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        # Payment statistics
        paid_orders = Order.objects.filter(payment_status=True, created_at__date__gte=month_ago)
        pending_orders = Order.objects.filter(payment_status=False, created_at__date__gte=month_ago)
        
        # Create category pie chart
        category_data = OrderItem.objects.values('product__category__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        fig = px.pie(
            names=[item['product__category__name'] for item in category_data],
            values=[item['count'] for item in category_data],
            title="Orders by Category",
            template="plotly_dark"
        )
        fig.update_traces(marker=dict(line=dict(color='#1a1a1a', width=2)))
        category_chart = plot(fig, output_type='div', include_plotlyjs='cdn')
        
        # Calculate average order value
        avg_order_value = 0
        if week_orders.count() > 0:
            total_week_revenue = week_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
            avg_order_value = total_week_revenue / week_orders.count()
        
        context = {
            'today_orders': today_orders.count(),
            'week_orders': week_orders.count(),
            'month_orders': month_orders.count(),
            'today_revenue': today_revenue,
            'week_revenue': week_revenue,
            'month_revenue': month_revenue,
            'paid_orders': paid_orders.count(),
            'pending_orders': pending_orders.count(),
            'category_chart': category_chart,
            'avg_order_value': avg_order_value,
            'title': 'Advanced Analytics Dashboard'
        }
        
        return TemplateResponse(request, 'admin/analytics_dashboard.html', context)
    
    def alerts_view(self, request):
        """Alert management view"""
        check_and_create_alerts()
        
        alerts = AdminAlert.objects.all().order_by('-created_at')
        unread_count = alerts.filter(is_read=False).count()
        
        # Mark as read
        if request.method == 'POST':
            alert_id = request.POST.get('alert_id')
            if alert_id:
                alert = AdminAlert.objects.get(id=alert_id)
                alert.is_read = True
                alert.read_by = request.user
                alert.save()
        
        context = {
            'alerts': alerts[:50],
            'unread_count': unread_count,
            'title': 'System Alerts & Notifications'
        }
        
        return TemplateResponse(request, 'admin/alerts.html', context)
    
    def index(self, request, extra_context=None):
        """Enhanced dashboard with alerts and stats"""
        extra_context = extra_context or {}
        
        check_and_create_alerts()
        
        today = timezone.now().date()
        
        # Core statistics
        today_orders = Order.objects.filter(created_at__date=today)
        today_revenue = today_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        total_revenue = Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        total_products = Product.objects.count()
        out_of_stock = Product.objects.filter(stock=0).count()
        low_stock = Product.objects.filter(stock__gt=0, stock__lt=10).count()
        
        total_subscribers = NewsletterSubscriber.objects.count()
        active_subscribers = NewsletterSubscriber.objects.filter(is_active=True).count()
        
        # Alerts
        alerts = AdminAlert.objects.filter(is_read=False).order_by('-severity', '-created_at')[:5]
        unread_alerts = AdminAlert.objects.filter(is_read=False).count()
        
        extra_context.update({
            'today_orders': today_orders.count(),
            'today_revenue': today_revenue,
            'total_revenue': total_revenue,
            'total_products': total_products,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'total_subscribers': total_subscribers,
            'active_subscribers': active_subscribers,
            'unread_alerts': unread_alerts,
            'recent_alerts': alerts,
        })
        
        return super().index(request, extra_context)


# ========================
# CATEGORY ADMIN
# ========================

class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'subcategories_count')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubCategoryInline]
    
    def subcategories_count(self, obj):
        count = obj.subcategories.count()
        return format_html(f'<span style="background-color: #ff6f91; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    subcategories_count.short_description = "Subcategories"


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name','category', 'slug')
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'category__name')


@admin.register(FeatureReason)
class FeatureReasonAdmin(admin.ModelAdmin):
    list_display = ('Reason',)


# ========================
# PRODUCT ADMIN (WITH EXPORTS)
# ========================

class MoreImagesInline(admin.TabularInline):
    model = MoreImages
    extra = 1
    fields = ('image', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px; border-radius: 5px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = ProductResource
    
    list_display = ('product_name_with_image', 'get_price_display', 'stock_status', 'subcategory', 'is_featured', 'get_colors', 'created_at')
    search_fields = ('name', 'description', 'slug')
    list_filter = ('price', 'tags', 'subcategory', 'is_featured', 'color', 'size', 'brand', 'created_at')
    filter_horizontal = ('tags',)
    inlines = [MoreImagesInline]
    readonly_fields = ('slug', 'image_preview', 'discount_percentage_display', 'created_at')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'description', 'image', 'image_preview')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'discount_price', 'discount_percentage_display', 'stock')
        }),
        ('Categorization', {
            'fields': ('subcategory', 'tags')
        }),
        ('Product Attributes', {
            'fields': ('color', 'size', 'brand')
        }),
        ('Featured', {
            'fields': ('is_featured', 'feature_reason')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def product_name_with_image(self, obj):
        if obj.image:
            return format_html(
                '<div style="display: flex; align-items: center;"><img src="{}" style="height: 40px; border-radius: 5px; margin-right: 10px;" /><strong>{}</strong></div>',
                obj.image.url, obj.name
            )
        return obj.name
    product_name_with_image.short_description = "Product"
    
    def get_price_display(self, obj):
        if obj.discount_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">৳{}</span> <strong style="color: #ff6f91;">৳{}</strong>',
                obj.price, obj.discount_price
            )
        return format_html('<strong>৳{}</strong>', obj.price)
    get_price_display.short_description = "Price"
    
    def stock_status(self, obj):
        if obj.stock == 0:
            return format_html('<span style="background-color: #f8d7da; color: #721c24; padding: 5px 10px; border-radius: 3px; font-weight: bold;">Out of Stock</span>')
        elif obj.stock < 10:
            return format_html('<span style="background-color: #fff3cd; color: #856404; padding: 5px 10px; border-radius: 3px; font-weight: bold;">Low ({} left)</span>', obj.stock)
        return format_html('<span style="background-color: #d4edda; color: #155724; padding: 5px 10px; border-radius: 3px; font-weight: bold;">In Stock ({})</span>', obj.stock)
    stock_status.short_description = "Stock"
    
    def get_colors(self, obj):
        if obj.color:
            return obj.color.name
        return "-"
    get_colors.short_description = "Color"
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 200px; border-radius: 5px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"
    
    def discount_percentage_display(self, obj):
        return format_html('<strong>{:.1f}%</strong>', obj.discount_percentage) if obj.discount_percentage > 0 else "-"
    discount_percentage_display.short_description = "Discount %"
    
    def save_model(self, request, obj, form, change):
        if obj.subcategory:
            obj.category = obj.subcategory.category
        super().save_model(request, obj, form, change)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'get_rating_display', 'created_at')
    list_filter = ('rating', 'created_at', 'product')
    search_fields = ('product__name', 'user__username', 'comment')
    readonly_fields = ('created_at',)
    
    def get_rating_display(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span style="font-size: 18px;">{}</span> <strong>{}/5</strong>', stars, obj.rating)
    get_rating_display.short_description = "Rating"
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    
    def products_count(self, obj):
        count = obj.product_set.count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    
    def products_count(self, obj):
        count = obj.product_set.count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand_logo', 'products_count')
    search_fields = ('name',)
    readonly_fields = ('brand_logo',)
    
    def brand_logo(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 40px; border-radius: 3px;" />', obj.image.url)
        return "-"
    brand_logo.short_description = "Logo"
    
    def products_count(self, obj):
        count = obj.product_set.count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    
    def products_count(self, obj):
        count = obj.products.count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


@admin.register(MoreImages)
class MoreImagesAdmin(admin.ModelAdmin):
    list_display = ('product', 'image_preview')
    list_filter = ('product',)
    search_fields = ('product__name',)
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px; border-radius: 5px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"


# ========================
# NEWSLETTER ADMIN (WITH BULK EMAIL & EXPORT)
# ========================

class EmailForm(forms.Form):
    subject = forms.CharField(max_length=100, required=True)
    message = forms.CharField(widget=CKEditor5Widget(config_name='default'), required=True)
    send_to_inactive = forms.BooleanField(required=False, initial=False)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = NewsletterSubscriberResource
    
    list_display = ('email', 'subscribed_at', 'is_active_badge', 'source')
    list_filter = ('is_active', 'subscribed_at', 'source')
    search_fields = ('email', 'source')
    date_hierarchy = 'subscribed_at'
    actions = ['mark_active', 'mark_inactive', 'send_email_to_selected']
    readonly_fields = ('subscribed_at',)
    
    fieldsets = (
        ('Subscriber Information', {
            'fields': ('email', 'source', 'subscribed_at')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background-color: #d4edda; color: #155724; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✅ Active</span>')
        return format_html('<span style="background-color: #f8d7da; color: #721c24; padding: 5px 10px; border-radius: 3px; font-weight: bold;">❌ Inactive</span>')
    is_active_badge.short_description = "Status"
    
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscribers marked as active.')
    mark_active.short_description = "Mark as active"
    
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscribers marked as inactive.')
    mark_inactive.short_description = "Mark as inactive"
    
    def send_email_to_selected(self, request, queryset):
        selected: list[Any] = list(queryset.values_list('pk', flat=True))
        request.session['selected_subscribers'] = selected
        return HttpResponseRedirect("send-newsletter-email/")
    send_email_to_selected.short_description = "Send email to selected"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls: list[URLResolver | URLPattern] = [
            path(
                'send-newsletter-email/', 
                self.admin_site.admin_view(self.send_newsletter_email_view), 
                name='send-newsletter-email'
            ),
        ]
        # PREPEND custom_urls to ensure they are evaluated first
        return custom_urls + urls
    
    def send_newsletter_email_view(self, request):
        selected_ids = request.session.get('selected_subscribers', [])
        subscribers = NewsletterSubscriber.objects.filter(pk__in=selected_ids)
        
        if request.method == 'POST':
            form = EmailForm(request.POST)
            if form.is_valid():
                subject = form.cleaned_data['subject']
                message = form.cleaned_data['message']
                send_to_inactive = form.cleaned_data['send_to_inactive']
                
                if not send_to_inactive:
                    subscribers = subscribers.filter(is_active=True)
                
                # Bulk send
                recipient_list = [sub.email for sub in subscribers]
                
                try:
                    connection = get_connection()
                    messages = []
                    
                    for email in recipient_list:
                        mail = EmailMultiAlternatives(
                            subject=subject,
                            body=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[email],
                            connection=connection
                        )
                        mail.attach_alternative(message, "text/html")
                        messages.append(mail)
                    
                    connection.send_messages(messages)
                    self.message_user(request, f"Successfully sent {len(recipient_list)} emails!")
                    
                    if 'selected_subscribers' in request.session:
                        del request.session['selected_subscribers']
                    
                    return HttpResponseRedirect("../")
                except Exception as e:
                    self.message_user(request, f"Error: {str(e)}", level='ERROR')
        else:
            form = EmailForm()
        
        context = {
            'form': form,
            'subscribers': subscribers,
            'opts': self.model._meta,
            'title': 'Send Email to Subscribers',
        }
        return TemplateResponse(request, 'admin/send_newsletter.html', context)
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ========================
# ORDER ADMIN (WITH EXPORTS & AUDIT)
# ========================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_price', 'quantity']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = OrderResource
    inlines = [OrderItemInline]

    list_display = ['order_id', 'get_customer_name', 'get_total_display', 'get_status_badge', 'get_payment_badge', 'created_at']
    list_filter = ['order_status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['id', 'user__username', 'full_name', 'email', 'phone']
    readonly_fields = ['user', 'full_name', 'email', 'phone', 'original_price', 'shipping_cost', 
                      'discount_amount', 'total_price', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = [
        ('Order Information', {
            'fields': ['order_status', 'user', 'full_name', 'email', 'phone', 'created_at', 'updated_at']
        }),
        ('Addresses', {
            'fields': ['shipping_address', 'billing_address']
        }),
        ('Payment Information', {
            'fields': ['payment_method', 'payment_status', 'transaction_id', 'sender_number']
        }),
        ('Manual Payment Workflow (NEW)', {
            'fields': ['delivery_charge_paid', 'delivery_payment_method', 'delivery_transaction_id'],
            'classes': ('collapse',)
        }),
        ('Financial Details', {
            'fields': ['original_price', 'shipping_cost', 'discount_amount', 'total_price']
        }),
        ('Shipping Details', {
            'fields': ['tracking_number', 'estimated_delivery']
        }),
        ('Notes', {
            'fields': ['notes']
        }),
    ]

    def order_id(self, obj):
        return format_html('<strong>#{}</strong>', obj.id)
    order_id.short_description = "Order ID"

    def get_customer_name(self, obj):
        return obj.full_name
    get_customer_name.short_description = "Customer"

    def get_total_display(self, obj):
        total = float(obj.total_price)
        return format_html('<strong style="color: #ff6f91; font-size: 14px;">{}</strong>', f'৳{total:,.2f}')
    get_total_display.short_description = "Total"

    def get_status_badge(self, obj):
        colors = {
            'pending': '#fff3cd',
            'processing': '#cfe2ff',
            'shipped': '#d1ecf1',
            'delivered': '#d4edda',
            'cancelled': '#f8d7da',
            'refunded': '#f5c6cb',
        }
        text_colors = {
            'pending': '#856404',
            'processing': '#084298',
            'shipped': '#055160',
            'delivered': '#155724',
            'cancelled': '#721c24',
            'refunded': '#721c24',
        }
        color = colors.get(obj.order_status, '#ccc')
        text_color = text_colors.get(obj.order_status, '#000')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, text_color, obj.get_order_status_display()
        )
    get_status_badge.short_description = "Status"

    def get_payment_badge(self, obj):
        if obj.payment_status:
            return format_html('<span style="background-color: #d4edda; color: #155724; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✅ Paid</span>')
        return format_html('<span style="background-color: #fff3cd; color: #856404; padding: 5px 10px; border-radius: 3px; font-weight: bold;">⏳ Pending</span>')
    get_payment_badge.short_description = "Payment"

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'get_price_display', 'quantity', 'get_total')
    list_filter = ('order__order_status', 'order__created_at')
    search_fields = ('product_name', 'order__id')
    readonly_fields = ('order', 'product', 'product_name', 'product_price', 'quantity')
    
    def get_price_display(self, obj):
        return format_html('৳{}', obj.product_price)
    get_price_display.short_description = "Unit Price"
    
    def get_total(self, obj):
        total = obj.product_price * obj.quantity
        return format_html('<strong>৳{:,.2f}</strong>', total)
    get_total.short_description = "Total"
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False  # Protect order items


# ========================
# ADDRESSES & COUPONS
# ========================

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'city', 'get_address_type_badge', 'user', 'default_badge', 'created_at']
    list_filter = ['address_type', 'city', 'created_at', 'country']
    search_fields = ['full_name', 'address_line1', 'city', 'phone', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
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
    
    def get_address_type_badge(self, obj):
        if obj.address_type == 'shipping':
            return format_html('<span style="background-color: #cfe2ff; color: #084298; padding: 5px 10px; border-radius: 3px; font-weight: bold;">📦 Shipping</span>')
        return format_html('<span style="background-color: #e2e3e5; color: #383d41; padding: 5px 10px; border-radius: 3px; font-weight: bold;">💳 Billing</span>')
    get_address_type_badge.short_description = "Type"
    
    def default_badge(self, obj):
        if obj.default:
            return format_html('<span style="background-color: #d4edda; color: #155724; padding: 5px 10px; border-radius: 3px; font-weight: bold;">⭐ Default</span>')
        return "-"
    default_badge.short_description = "Default"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_display', 'minimum_order_value', 'get_active_badge', 'validity_display', 'usage_display')
    list_filter = ('is_active', 'valid_from', 'valid_to')
    search_fields = ('code',)
    readonly_fields = ('used_count', 'is_valid_display')
    
    fieldsets = (
        ("Coupon Information", {
            'fields': ('code', 'is_active', 'is_valid_display')
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
            return format_html('<strong style="color: #ff6f91;">৳{}</strong>', obj.discount_amount)
        return format_html('<strong style="color: #667bc6;">{}%</strong>', obj.discount_percent)
    discount_display.short_description = "Discount"
    
    def get_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background-color: #d4edda; color: #155724; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✅ Active</span>')
        return format_html('<span style="background-color: #f8d7da; color: #721c24; padding: 5px 10px; border-radius: 3px; font-weight: bold;">❌ Inactive</span>')
    get_active_badge.short_description = "Status"
    
    def validity_display(self, obj):
        return format_html('{} → {}', obj.valid_from.strftime('%Y-%m-%d'), obj.valid_to.strftime('%Y-%m-%d'))
    validity_display.short_description = "Valid Period"
    
    def usage_display(self, obj):
        if obj.usage_limit == 0:
            return format_html('<span style="background-color: #e2e3e5; color: #383d41; padding: 3px 8px; border-radius: 3px;">Unlimited ({} used)</span>', obj.used_count)
        remaining = obj.usage_limit - obj.used_count
        return format_html(
            '<span style="background-color: #d1ecf1; color: #055160; padding: 3px 8px; border-radius: 3px;">{}/{} ({} left)</span>',
            obj.used_count, obj.usage_limit, remaining
        )
    usage_display.short_description = "Usage"
    
    def is_valid_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: green; font-weight: bold;">Currently valid</span>')
        return format_html('<span style="color: red; font-weight: bold;">Not valid</span>')
    is_valid_display.short_description = "Valid Now"


# ========================
# ADMIN ALERT & AUDIT LOG
# ========================

@admin.register(AdminAlert)
class AdminAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type_badge', 'severity_badge', 'is_read_badge', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_read', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('title', 'message', 'alert_type', 'severity')
        }),
        ('Related Objects', {
            'fields': ('product', 'order')
        }),
        ('Status', {
            'fields': ('is_read', 'read_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        return False
    
    def alert_type_badge(self, obj):
        icons = {
            'low_stock': '📦',
            'high_orders': '📈',
            'failed_payment': '❌',
            'system': '⚙️'
        }
        icon = icons.get(obj.alert_type, '•')
        return format_html('{} {}', icon, obj.get_alert_type_display())
    alert_type_badge.short_description = "Type"
    
    def severity_badge(self, obj):
        colors = {
            'info': '#17a2b8',
            'warning': '#ffc107',
            'critical': '#dc3545'
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_severity_display().upper()
        )
    severity_badge.short_description = "Severity"
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Unread</span>')
    is_read_badge.short_description = "Status"


# Register custom admin site
admin.site.__class__ = IWMAdminSite
