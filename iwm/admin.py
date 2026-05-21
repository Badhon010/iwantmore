from django.urls.resolvers import URLPattern, URLResolver
from typing import Any
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
# Delayed imports to avoid circular dependency
# from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count, Q, F, DecimalField
from django.utils import timezone
from django import forms
from django.conf import settings
from datetime import timedelta, datetime, time
import json
import csv

from import_export import resources
from import_export.admin import ExportActionMixin

import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django_ckeditor_5.widgets import CKEditor5Widget
import logging
from unfold.admin import ModelAdmin, TabularInline
from unfold.sites import UnfoldAdminSite

from .models import (
    Product, Review, Tag, MoreImages, NewsletterSubscriber,
    Category, SubCategory, FeatureReason, Order, OrderItem,
    Address, Coupon, Color, Size, Brand, AdminAlert
)

CAPTURED_PAYMENT_STATES = ['paid', 'partially_paid']
FOLLOW_UP_PAYMENT_STATES = ['awaiting_payment', 'payment_submitted']
logger = logging.getLogger(__name__)


def _as_local_aware(value):
    if timezone.is_aware(timezone.now()) and timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _day_range(day):
    return (
        _as_local_aware(datetime.combine(day, time.min)),
        _as_local_aware(datetime.combine(day, time.max)),
    )


def _validation_error_message(exc):
    if hasattr(exc, 'message_dict') and exc.message_dict:
        first_error_list = next(iter(exc.message_dict.values()))
        if first_error_list:
            return str(first_error_list[0])

    if hasattr(exc, 'messages') and exc.messages:
        return str(exc.messages[0])

    return str(exc)


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
        fields = ('id', 'full_name', 'email', 'phone', 'total_price', 'payment_state', 'order_status', 'created_at')


class NewsletterSubscriberResource(resources.ModelResource):
    class Meta:
        model = NewsletterSubscriber
        fields = ('id', 'email', 'source', 'is_active', 'subscribed_at')


# ========================
# AUTOMATED ALERTS
# ========================

def check_and_create_alerts():
    """Check all alert conditions and create necessary alerts"""
    today = timezone.localdate()
    today_start, today_end = _day_range(today)

    # Low stock
    low_stock_products = list(
        Product.objects.filter(stock__lt=10, stock__gt=0).only('id', 'name', 'stock')
    )
    existing_low_stock_alerts = set(
        AdminAlert.objects.filter(
            alert_type='low_stock',
            is_read=False,
            created_at__range=(today_start, today_end),
            product_id__in=[product.id for product in low_stock_products],
        ).values_list('product_id', flat=True)
    )
    AdminAlert.objects.bulk_create([
        AdminAlert(
            alert_type='low_stock',
            severity='warning',
            title=f"Low Stock: {product.name}",
            message=f"Product '{product.name}' has only {product.stock} units left.",
            product=product,
        )
        for product in low_stock_products
        if product.id not in existing_low_stock_alerts
    ])
    
    # High orders
    today_orders = Order.objects.filter(created_at__range=(today_start, today_end)).count()
    if today_orders > 20:
        if not AdminAlert.objects.filter(
            alert_type='high_orders',
            is_read=False,
            created_at__range=(today_start, today_end)
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
        payment_state__in=FOLLOW_UP_PAYMENT_STATES,
        order_status__in=['pending', 'processing'],
        created_at__lt=threshold
    ).only('id', 'full_name')
    existing_failed_payment_alerts = set(
        AdminAlert.objects.filter(
            alert_type='failed_payment',
            is_read=False,
            order_id__in=failed_payments.values_list('id', flat=True),
        ).values_list('order_id', flat=True)
    )
    AdminAlert.objects.bulk_create([
        AdminAlert(
            alert_type='failed_payment',
            severity='critical',
            title=f"Unpaid Order: #{order.id}",
            message=f"Order #{order.id} from {order.full_name} hasn't been paid for over 24 hours.",
            order=order,
        )
        for order in failed_payments
        if order.id not in existing_failed_payment_alerts
    ])


# ========================
# CUSTOM ADMIN SITE WITH CHARTS
# ========================

class IWMAdminSite(UnfoldAdminSite):
    site_header = "I Want More Admin"
    site_title = "I Want More Admin Panel"
    index_title = "Dashboard"
    index_template = "admin/custom_index.html"
    
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
            date = timezone.localdate() - timedelta(days=i)
            day_start, day_end = _day_range(date)
            revenue = Order.objects.filter(
                created_at__range=(day_start, day_end),
                payment_state__in=CAPTURED_PAYMENT_STATES
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
        
        context = {**self.each_context(request),
            'chart': chart_html,
            'title': 'Revenue Trend Chart'
        }
        return TemplateResponse(request, 'admin/revenue_chart.html', context)
    
    def analytics_view(self, request):
        """Comprehensive analytics dashboard"""
        check_and_create_alerts()
        
        today = timezone.localdate()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        today_start, today_end = _day_range(today)
        week_start, _week_end = _day_range(week_ago)
        month_start, _month_end = _day_range(month_ago)
        
        # Order statistics
        today_orders = Order.objects.filter(created_at__range=(today_start, today_end))
        week_orders = Order.objects.filter(created_at__range=(week_start, today_end))
        month_orders = Order.objects.filter(created_at__range=(month_start, today_end))
        
        today_revenue = today_orders.filter(payment_state__in=CAPTURED_PAYMENT_STATES).aggregate(Sum('total_price'))['total_price__sum'] or 0
        week_revenue = week_orders.filter(payment_state__in=CAPTURED_PAYMENT_STATES).aggregate(Sum('total_price'))['total_price__sum'] or 0
        month_revenue = month_orders.filter(payment_state__in=CAPTURED_PAYMENT_STATES).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        # Payment statistics
        paid_orders = month_orders.filter(payment_state__in=CAPTURED_PAYMENT_STATES)
        pending_orders = month_orders.filter(payment_state__in=FOLLOW_UP_PAYMENT_STATES)
        payment_state_counts = [
            {
                'label': label,
                'count': month_orders.filter(payment_state=state).count(),
            }
            for state, label in Order.PAYMENT_STATE_CHOICES
        ]

        # Create category pie chart
        category_data = list(OrderItem.objects.filter(
            order__created_at__range=(month_start, today_end)
        ).exclude(
            product__category__name__isnull=True
        ).values('product__category__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10])

        if category_data:
            fig = px.pie(
                names=[item['product__category__name'] for item in category_data],
                values=[item['count'] for item in category_data],
                title="Orders by Category",
                template="plotly_dark"
            )
            fig.update_traces(marker=dict(line=dict(color='#1a1a1a', width=2)))
            category_chart = plot(fig, output_type='div', include_plotlyjs='cdn')
        else:
            category_chart = format_html(
                '<div style="padding: 2rem; text-align: center; color: #9ca3af;">No category data available for the selected period.</div>'
            )
        
        # Calculate average order value
        avg_order_value = 0
        paid_week_orders = week_orders.filter(payment_state__in=CAPTURED_PAYMENT_STATES)
        if paid_week_orders.count() > 0:
            total_week_revenue = paid_week_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
            avg_order_value = total_week_revenue / paid_week_orders.count()

        repeat_customers = month_orders.exclude(email='').values('email').annotate(order_count=Count('id')).filter(order_count__gt=1).count()
        total_customers = month_orders.exclude(email='').values('email').distinct().count()
        delivered_orders = month_orders.filter(order_status='delivered').count()
        cancelled_orders = month_orders.filter(order_status='cancelled').count()
        top_products = OrderItem.objects.filter(order__created_at__range=(month_start, today_end)).values('product_name').annotate(
            total_quantity=Sum('quantity')
        ).order_by('-total_quantity')[:5]
        
        context = {**self.each_context(request),
            'today_orders': today_orders.count(),
            'week_orders': week_orders.count(),
            'month_orders': month_orders.count(),
            'today_revenue': today_revenue,
            'week_revenue': week_revenue,
            'month_revenue': month_revenue,
            'paid_orders': paid_orders.count(),
            'pending_orders': pending_orders.count(),
            'payment_state_labels': json.dumps([item['label'] for item in payment_state_counts]),
            'payment_state_values': json.dumps([item['count'] for item in payment_state_counts]),
            'category_chart': category_chart,
            'avg_order_value': avg_order_value,
            'repeat_customers': repeat_customers,
            'total_customers': total_customers,
            'delivered_orders': delivered_orders,
            'cancelled_orders': cancelled_orders,
            'top_products': top_products,
            'title': 'Advanced Analytics Dashboard'
        }
        
        return TemplateResponse(request, 'admin/analytics_dashboard.html', context)
    
    def alerts_view(self, request):
        """Alert management view"""
        check_and_create_alerts()
        
        alerts = AdminAlert.objects.select_related('product', 'order', 'read_by').order_by('-created_at')
        unread_count = alerts.filter(is_read=False).count()
        
        # Mark as read
        if request.method == 'POST':
            alert_id = request.POST.get('alert_id')
            if alert_id:
                AdminAlert.objects.filter(id=alert_id).update(is_read=True, read_by=request.user)
        
        context = {**self.each_context(request),
            'alerts': alerts[:50],
            'unread_count': unread_count,
            'title': 'System Alerts & Notifications'
        }
        
        return TemplateResponse(request, 'admin/alerts.html', context)
    
    def index(self, request, extra_context=None):
        """Enhanced dashboard with alerts and stats"""
        extra_context = extra_context or {}
        
        check_and_create_alerts()
        
        today = timezone.localdate()
        today_start, today_end = _day_range(today)
        
        # Core statistics
        today_orders = Order.objects.filter(created_at__range=(today_start, today_end))
        today_revenue = today_orders.filter(payment_state__in=CAPTURED_PAYMENT_STATES).aggregate(Sum('total_price'))['total_price__sum'] or 0
        total_revenue = Order.objects.filter(payment_state__in=CAPTURED_PAYMENT_STATES).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
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
# INSTANTIATE CUSTOM ADMIN SITE FIRST
# ========================

# Instantiate the custom admin site for use in urls.py
admin_site = IWMAdminSite(name='admin')


# ========================
# CATEGORY ADMIN
# ========================

class SubCategoryInline(TabularInline):
    model = SubCategory
    extra = 1


class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'subcategories_count')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubCategoryInline]
    
    def subcategories_count(self, obj):
        count = obj.subcategories.count()
        return format_html(f'<span style="background-color: #ff6f91; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    subcategories_count.short_description = "Subcategories"


class SubCategoryAdmin(ModelAdmin):
    list_display = ('name','category', 'slug')
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'category__name')


class FeatureReasonAdmin(ModelAdmin):
    list_display = ('Reason',)


# ========================
# PRODUCT ADMIN (WITH EXPORTS)
# ========================

class MoreImagesInline(TabularInline):
    model = MoreImages
    extra = 1
    fields = ('image', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px; border-radius: 5px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"


class ProductAdmin(ExportActionMixin, ModelAdmin):
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
        return format_html('<strong>{}</strong>', f"{float(obj.discount_percentage):.1f}%") if getattr(obj, "discount_percentage", 0) and obj.discount_percentage > 0 else "-"
    discount_percentage_display.short_description = "Discount %"
    
    def save_model(self, request, obj, form, change):
        if obj.subcategory:
            obj.category = obj.subcategory.category
        super().save_model(request, obj, form, change)


class ReviewAdmin(ModelAdmin):
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


class ColorAdmin(ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    
    def products_count(self, obj):
        count = obj.product_set.count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


class SizeAdmin(ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    
    def products_count(self, obj):
        count = obj.product_set.count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


class BrandAdmin(ModelAdmin):
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


class TagAdmin(ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    
    def products_count(self, obj):
        count = obj.products.count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


class MoreImagesAdmin(ModelAdmin):
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


class NewsletterSubscriberAdmin(ExportActionMixin, ModelAdmin):
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
        selected_subscribers = list(subscribers)
        subscriber_count = len(selected_subscribers)
        
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
                except Exception:
                    logger.exception('Newsletter bulk send failed for %s recipients.', len(recipient_list))
                    self.message_user(
                        request,
                        "Could not send the newsletter right now. Check the logs and email configuration.",
                        level='ERROR',
                    )
        else:
            form = EmailForm()
        
        context = {**self.admin_site.each_context(request),
            'form': form,
            'subscribers': selected_subscribers,
            'subscriber_count': subscriber_count,
            'opts': self.model._meta,
            'title': 'Send Email to Subscribers',
        }
        return TemplateResponse(request, 'admin/send_newsletter.html', context)
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ========================
# ORDER ADMIN (WITH EXPORTS & AUDIT)
# ========================

class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_price', 'quantity']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class OrderAdmin(ExportActionMixin, ModelAdmin):
    form = OrderAdminForm
    resource_class = OrderResource
    inlines = [OrderItemInline]
    actions = [
        'mark_payment_submitted',
        'mark_partially_paid',
        'mark_paid',
        'mark_failed',
        'mark_refunded',
        'mark_cancelled',
        'mark_processing',
        'mark_shipped',
        'mark_delivered',
        'mark_delivery_charge_paid',
    ]
    list_display = ['order_id', 'get_customer_name', 'get_total_display', 'get_status_badge', 'get_payment_badge', 'created_at']
    list_filter = ['order_status', 'payment_state', 'payment_method', 'created_at']
    search_fields = ['id', 'user__username', 'full_name', 'email', 'phone']
    readonly_fields = ['user', 'full_name', 'email', 'phone', 'original_price', 'shipping_cost', 
                      'discount_amount', 'total_price', 'coupon', 'inventory_restored_at',
                      'coupon_usage_released_at', 'created_at', 'updated_at']
    list_select_related = ['user', 'shipping_address', 'billing_address', 'coupon']
    date_hierarchy = 'created_at'

    fieldsets = [
        ('Order Information', {
            'fields': ['order_status', 'user', 'full_name', 'email', 'phone', 'coupon', 'created_at', 'updated_at']
        }),
        ('Addresses', {
            'fields': ['shipping_address', 'billing_address']
        }),
        ('Payment Information', {
            'fields': ['payment_method', 'payment_state', 'transaction_id', 'sender_number']
        }),
        ('Manual Payment Workflow (NEW)', {
            'fields': ['delivery_charge_paid', 'delivery_payment_method', 'delivery_sender_number', 'delivery_transaction_id'],
            'classes': ('collapse',)
        }),
        ('Recovery Tracking', {
            'fields': ['inventory_restored_at', 'coupon_usage_released_at'],
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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'shipping_address', 'billing_address', 'coupon')

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

    def _legacy_simple_payment_badge(self, obj):
        if obj.payment_state == 'paid':
            return format_html('<span style="background-color: #d4edda; color: #155724; padding: 5px 10px; border-radius: 3px; font-weight: bold;">✅ Paid</span>')
        return format_html('<span style="background-color: #fff3cd; color: #856404; padding: 5px 10px; border-radius: 3px; font-weight: bold;">⏳ Pending</span>')
    _legacy_simple_payment_badge.short_description = "Payment"

    def get_payment_badge(self, obj):
        colors = {
            'awaiting_payment': ('#fff3cd', '#856404', 'Awaiting Payment'),
            'payment_submitted': ('#cfe2ff', '#084298', 'Submitted'),
            'partially_paid': ('#d1ecf1', '#055160', 'Partial'),
            'paid': ('#d4edda', '#155724', 'Paid'),
            'failed': ('#f8d7da', '#721c24', 'Failed'),
            'refunded': ('#f5c6cb', '#721c24', 'Refunded'),
        }
        background, color, label = colors.get(
            obj.payment_state,
            ('#e2e3e5', '#383d41', obj.get_payment_state_display()),
        )
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            background,
            color,
            label,
        )
    get_payment_badge.short_description = "Payment"

    def _run_order_action(self, request, queryset, *, order_status=None, payment_state=None, record_delivery_charge=False):
        updated = 0
        skipped = []

        for order in queryset.select_related('coupon').order_by('id'):
            try:
                changed = False
                if payment_state == 'refunded':
                    changed = order.transition_payment_state('refunded') or changed
                elif order_status == 'refunded':
                    changed = order.transition_order_status('refunded') or changed
                else:
                    if payment_state and payment_state != order.payment_state:
                        changed = order.transition_payment_state(payment_state) or changed
                    if order_status and order_status != order.order_status:
                        changed = order.transition_order_status(order_status) or changed
                    if record_delivery_charge:
                        changed = order.mark_delivery_charge_paid() or changed

                if changed:
                    updated += 1
            except ValidationError as exc:
                skipped.append(f"#{order.id}: {_validation_error_message(exc)}")

        if updated:
            self.message_user(request, f'{updated} order(s) updated successfully.', level=messages.SUCCESS)
        if skipped:
            self.message_user(
                request,
                'Skipped ' + '; '.join(skipped[:5]),
                level=messages.WARNING,
            )

    def save_model(self, request, obj, form, change):
        if not change:
            return super().save_model(request, obj, form, change)

        lifecycle_fields = {'order_status', 'payment_state', 'delivery_charge_paid'}
        non_lifecycle_fields = [field for field in form.changed_data if field not in lifecycle_fields]

        with transaction.atomic():
            locked_order = Order.objects.select_for_update().get(pk=obj.pk)

            for field in non_lifecycle_fields:
                setattr(locked_order, field, form.cleaned_data[field])

            if non_lifecycle_fields:
                locked_order.save(update_fields=non_lifecycle_fields)

            requested_status = form.cleaned_data.get('order_status', locked_order.order_status)
            requested_payment_state = form.cleaned_data.get('payment_state', locked_order.payment_state)
            requested_delivery_paid = form.cleaned_data.get('delivery_charge_paid', locked_order.delivery_charge_paid)

            if requested_payment_state == 'refunded' and requested_payment_state != locked_order.payment_state:
                locked_order._transition_payment_state_locked('refunded')
            elif requested_status == 'refunded' and requested_status != locked_order.order_status:
                locked_order._transition_order_status_locked('refunded')
            else:
                if requested_delivery_paid and not locked_order.delivery_charge_paid:
                    locked_order._mark_delivery_charge_paid_locked()

                if requested_payment_state != locked_order.payment_state:
                    locked_order._transition_payment_state_locked(requested_payment_state)

                if requested_status != locked_order.order_status:
                    locked_order._transition_order_status_locked(requested_status)

    def mark_payment_submitted(self, request, queryset):
        self._run_order_action(request, queryset, payment_state='payment_submitted')
    mark_payment_submitted.short_description = "Mark selected orders as payment submitted"

    def mark_partially_paid(self, request, queryset):
        self._run_order_action(request, queryset, payment_state='partially_paid')
    mark_partially_paid.short_description = "Mark selected orders as partially paid"

    def mark_paid(self, request, queryset):
        self._run_order_action(request, queryset, payment_state='paid')
    mark_paid.short_description = "Mark selected orders as paid"

    def mark_failed(self, request, queryset):
        self._run_order_action(request, queryset, payment_state='failed')
    mark_failed.short_description = "Mark selected orders as failed"

    def mark_refunded(self, request, queryset):
        self._run_order_action(request, queryset, payment_state='refunded')
    mark_refunded.short_description = "Mark selected orders as refunded"

    def mark_cancelled(self, request, queryset):
        self._run_order_action(request, queryset, order_status='cancelled')
    mark_cancelled.short_description = "Mark selected orders as cancelled"

    def mark_processing(self, request, queryset):
        self._run_order_action(request, queryset, order_status='processing')
    mark_processing.short_description = "Mark selected orders as processing"

    def mark_shipped(self, request, queryset):
        self._run_order_action(request, queryset, order_status='shipped')
    mark_shipped.short_description = "Mark selected orders as shipped"

    def mark_delivered(self, request, queryset):
        self._run_order_action(request, queryset, order_status='delivered')
    mark_delivered.short_description = "Mark selected orders as delivered"

    def mark_delivery_charge_paid(self, request, queryset):
        self._run_order_action(request, queryset, record_delivery_charge=True)
    mark_delivery_charge_paid.short_description = "Mark delivery charge as paid"

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False


class OrderItemAdmin(ModelAdmin):
    list_display = ('order', 'product_name', 'get_price_display', 'quantity', 'get_total')
    list_filter = ('order__order_status', 'order__created_at')
    search_fields = ('product_name', 'order__id')
    readonly_fields = ('order', 'product', 'product_name', 'product_price', 'quantity')
    
    def get_price_display(self, obj):
        return format_html('৳{}', obj.product_price)
    get_price_display.short_description = "Unit Price"
    
    def get_total(self, obj):
        total = float(obj.product_price * obj.quantity)
        return format_html('<strong>৳{}</strong>', f"{total:,.2f}")
    get_total.short_description = "Total"
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False  # Protect order items


# ========================
# ADDRESSES & COUPONS
# ========================

class AddressAdmin(ModelAdmin):
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


class CouponAdmin(ModelAdmin):
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

class AdminAlertAdmin(ModelAdmin):
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


# ========================
# USER & GROUP ADMIN
# ========================

# Import base admin classes here to avoid circular import at module level
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm


class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# ========================
# REGISTER ALL MODELS WITH CUSTOM ADMIN SITE
# ========================

# Unregister User and Group from default admin site if they were registered
try:
    admin_site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin_site.unregister(Group)
except admin.sites.NotRegistered:
    pass

# Register all models with the custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(SubCategory, SubCategoryAdmin)
admin_site.register(FeatureReason, FeatureReasonAdmin)
admin_site.register(Product, ProductAdmin)
admin_site.register(Review, ReviewAdmin)
admin_site.register(Color, ColorAdmin)
admin_site.register(Size, SizeAdmin)
admin_site.register(Brand, BrandAdmin)
admin_site.register(Tag, TagAdmin)
admin_site.register(MoreImages, MoreImagesAdmin)
admin_site.register(NewsletterSubscriber, NewsletterSubscriberAdmin)
admin_site.register(Order, OrderAdmin)
admin_site.register(OrderItem, OrderItemAdmin)
admin_site.register(Address, AddressAdmin)
admin_site.register(Coupon, CouponAdmin)
admin_site.register(AdminAlert, AdminAlertAdmin)
