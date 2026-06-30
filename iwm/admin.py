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
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Cast, TruncDate
from django.utils import timezone
from django import forms
from django.forms.models import BaseInlineFormSet
from django.conf import settings
from datetime import timedelta, datetime, time
from decimal import Decimal
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
    Product, ProductColorImage, Review, Tag, NewsletterSubscriber,
    Category, SubCategory, FeatureReason, Order, OrderItem,
    Address, Coupon, Color, Size, AdminAlert, PromoBanner, Slider
)

CAPTURED_PAYMENT_STATES = ['paid', 'partially_paid']
FOLLOW_UP_PAYMENT_STATES = ['awaiting_payment', 'payment_submitted']
logger = logging.getLogger(__name__)


def _unread_alerts_badge(request):
    count = AdminAlert.objects.filter(is_read=False).count()
    return str(count) if count else None


def _low_stock_badge(request):
    count = Product.objects.filter(stock__gt=0, stock__lt=10).count()
    return str(count) if count else None


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


def _money_output_field():
    return DecimalField(max_digits=12, decimal_places=2)


def _order_item_profit_expression():
    buying_price = Cast(F('product__buying_price'), output_field=_money_output_field())
    return ExpressionWrapper(
        F('quantity') * (F('product_price') - buying_price),
        output_field=_money_output_field(),
    )


def _parse_filter_date(raw_value):
    if not raw_value:
        return None

    try:
        return datetime.strptime(raw_value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _resolve_date_range(request, *, default_days=30):
    today = timezone.localdate()
    preset = (request.GET.get('range') or '').strip()
    default_start = today - timedelta(days=default_days - 1)

    start_date = _parse_filter_date(request.GET.get('start_date'))
    end_date = _parse_filter_date(request.GET.get('end_date'))

    preset_days = {
        'today': 1,
        '7': 7,
        '30': 30,
        '90': 90,
        '365': 365,
    }

    if start_date or end_date:
        start_date = start_date or default_start
        end_date = end_date or today
        selected_range = 'custom'
    else:
        selected_range = preset if preset in preset_days else str(default_days)
        days = preset_days.get(selected_range, default_days)
        start_date = today - timedelta(days=days - 1)
        end_date = today

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    if end_date > today:
        end_date = today

    if start_date > today:
        start_date = today

    return {
        'selected_range': selected_range,
        'start_date': start_date,
        'end_date': end_date,
    }


def _period_bounds(start_date, end_date):
    start_at, _ = _day_range(start_date)
    _, end_at = _day_range(end_date)
    return start_at, end_at


def _calculate_profit(start_date, end_date):
    start_at, end_at = _period_bounds(start_date, end_date)
    profit = OrderItem.objects.filter(
        order__created_at__range=(start_at, end_at),
        order__payment_state__in=CAPTURED_PAYMENT_STATES,
        product__isnull=False,
    ).aggregate(total=Sum(_order_item_profit_expression()))['total']
    return profit or Decimal('0.00')


def _summarize_orders(start_date, end_date):
    start_at, end_at = _period_bounds(start_date, end_date)
    summary = Order.objects.filter(created_at__range=(start_at, end_at)).aggregate(
        order_count=Count('id'),
        revenue=Sum('total_price', filter=Q(payment_state__in=CAPTURED_PAYMENT_STATES)),
        paid_orders=Count('id', filter=Q(payment_state__in=CAPTURED_PAYMENT_STATES)),
        pending_orders=Count('id', filter=Q(payment_state__in=FOLLOW_UP_PAYMENT_STATES)),
        delivered_orders=Count('id', filter=Q(order_status='delivered')),
        cancelled_orders=Count('id', filter=Q(order_status='cancelled')),
        total_customers=Count('email', filter=~Q(email=''), distinct=True),
    )
    summary['revenue'] = summary['revenue'] or Decimal('0.00')
    summary['profit'] = _calculate_profit(start_date, end_date)
    summary['avg_order_value'] = (
        summary['revenue'] / summary['paid_orders']
        if summary['paid_orders']
        else Decimal('0.00')
    )
    return summary


def _build_financial_chart_data(start_date, end_date):
    start_at, end_at = _period_bounds(start_date, end_date)
    points = {}
    current = start_date

    while current <= end_date:
        points[current.isoformat()] = {
            'label': current.strftime('%b %d'),
            'revenue': 0.0,
            'profit': 0.0,
        }
        current += timedelta(days=1)

    revenue_rows = Order.objects.filter(
        created_at__range=(start_at, end_at),
        payment_state__in=CAPTURED_PAYMENT_STATES,
    ).annotate(day=TruncDate('created_at')).values('day').annotate(
        revenue=Sum('total_price')
    ).order_by('day')

    profit_rows = OrderItem.objects.filter(
        order__created_at__range=(start_at, end_at),
        order__payment_state__in=CAPTURED_PAYMENT_STATES,
        product__isnull=False,
    ).annotate(day=TruncDate('order__created_at')).values('day').annotate(
        profit=Sum(_order_item_profit_expression())
    ).order_by('day')

    for row in revenue_rows:
        day = row['day']
        if day:
            points[day.isoformat()]['revenue'] = int(round(float(row['revenue'] or 0)))

    for row in profit_rows:
        day = row['day']
        if day:
            points[day.isoformat()]['profit'] = int(round(float(row['profit'] or 0)))

    ordered_points = list(points.values())
    return {
        'labels': [point['label'] for point in ordered_points],
        'revenue': [point['revenue'] for point in ordered_points],
        'profit': [point['profit'] for point in ordered_points],
    }


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

    # Low stock — one alert per product per day, regardless of read status
    low_stock_products = list(
        Product.objects.filter(stock__lt=10, stock__gt=0).only('id', 'name', 'stock')
    )
    existing_low_stock_alerts = set(
        AdminAlert.objects.filter(
            alert_type='low_stock',
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
    
    # High orders — one alert per day, regardless of read status
    today_orders = Order.objects.filter(created_at__range=(today_start, today_end)).count()
    if today_orders > 20:
        if not AdminAlert.objects.filter(
            alert_type='high_orders',
            created_at__range=(today_start, today_end)
        ).exists():
            AdminAlert.objects.create(
                alert_type='high_orders',
                severity='info',
                title="High Order Volume Detected",
                message=f"Today has {today_orders} orders - significantly higher than usual."
            )
    
    # Failed payments (pending > 24 hours) — one alert per order, regardless of read status
    threshold = timezone.now() - timedelta(hours=24)
    failed_payments = Order.objects.filter(
        payment_state__in=FOLLOW_UP_PAYMENT_STATES,
        order_status__in=['pending', 'processing'],
        created_at__lt=threshold
    ).only('id', 'full_name')
    existing_failed_payment_alerts = set(
        AdminAlert.objects.filter(
            alert_type='failed_payment',
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
            path('analytics/export-csv/', self.admin_view(self.analytics_export_csv), name='analytics-export-csv'),
            path('alerts/', self.admin_view(self.alerts_view), name='alerts'),
            path('clear-cache/', self.admin_view(self.clear_cache_view), name='clear-cache'),
        ]
        return custom_urls + urls
    
    def alerts_view(self, request):
        """Alert management view — with filter (AH3) and pagination (AH7)."""
        # PRG: mark as read on POST, then redirect to GET so refresh is safe.
        if request.method == 'POST':
            alert_id = request.POST.get('alert_id')
            if alert_id:
                AdminAlert.objects.filter(id=alert_id).update(is_read=True, read_by=request.user)
            return HttpResponseRedirect(request.path)

        check_and_create_alerts()

        # AH3: Read filter params from GET.  Each is validated against the
        # allowed choices so arbitrary values are silently ignored.
        VALID_SEVERITIES = {'info', 'warning', 'critical'}
        VALID_TYPES      = {'low_stock', 'high_orders', 'failed_payment', 'system'}
        VALID_STATUSES   = {'read', 'unread'}

        f_severity = request.GET.get('severity', '').strip()
        f_type     = request.GET.get('alert_type', '').strip()
        f_status   = request.GET.get('status', '').strip()

        # Validate — silently clear invalid values so URLs cannot inject bad SQL.
        if f_severity not in VALID_SEVERITIES:
            f_severity = ''
        if f_type not in VALID_TYPES:
            f_type = ''
        if f_status not in VALID_STATUSES:
            f_status = ''

        # Build filtered queryset; select_related avoids N+1 on product/order/user.
        qs = AdminAlert.objects.select_related('product', 'order', 'read_by').order_by('-created_at')
        if f_severity:
            qs = qs.filter(severity=f_severity)
        if f_type:
            qs = qs.filter(alert_type=f_type)
        if f_status == 'unread':
            qs = qs.filter(is_read=False)
        elif f_status == 'read':
            qs = qs.filter(is_read=True)

        # AH7: Paginate — 25 per page.  get_page() handles out-of-range safely.
        paginator = Paginator(qs, 25)
        page_obj  = paginator.get_page(request.GET.get('page', 1))

        # Keep unread_count from the unfiltered set so the badge stays accurate.
        unread_count = AdminAlert.objects.filter(is_read=False).count()

        context = {
            **self.each_context(request),
            'alerts':      page_obj,
            'page_obj':    page_obj,
            'paginator':   paginator,
            'unread_count': unread_count,
            'f_severity':  f_severity,
            'f_type':      f_type,
            'f_status':    f_status,
            'title': 'System Alerts & Notifications',
        }
        return TemplateResponse(request, 'admin/alerts.html', context)
    
    def clear_cache_view(self, request):
        """Clear all application cache"""
        from django.core.cache import cache
        cache.clear()
        messages.success(request, "Application cache has been cleared successfully.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))

    def analytics_export_csv(self, request):
        """Export the currently filtered revenue/profit data as a CSV download."""
        range_data = _resolve_date_range(request, default_days=30)
        chart_data = _build_financial_chart_data(
            range_data['start_date'],
            range_data['end_date'],
        )
        filename = f"analytics_{range_data['start_date']}_{range_data['end_date']}.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Revenue (Tk)', 'Profit (Tk)'])
        for i, label in enumerate(chart_data['labels']):
            writer.writerow([label, chart_data['revenue'][i], chart_data['profit'][i]])
        return response

    def revenue_chart_view(self, request):
        """AC1: Redirect to the Analytics Dashboard to avoid duplicating the same
        revenue/profit information that is already shown there with Chart.js."""
        return HttpResponseRedirect(reverse('admin:analytics'))

    def analytics_view(self, request):
        """Comprehensive analytics dashboard"""
        check_and_create_alerts()

        today = timezone.localdate()
        selected_range = _resolve_date_range(request, default_days=30)
        selected_start = selected_range['start_date']
        selected_end = selected_range['end_date']
        selected_start_at, selected_end_at = _period_bounds(selected_start, selected_end)

        today_summary = _summarize_orders(today, today)
        week_summary = _summarize_orders(today - timedelta(days=6), today)
        month_summary = _summarize_orders(today - timedelta(days=29), today)
        selected_summary = _summarize_orders(selected_start, selected_end)
        financial_chart_data = _build_financial_chart_data(selected_start, selected_end)

        selected_orders = Order.objects.filter(created_at__range=(selected_start_at, selected_end_at))
        payment_counts_map = {state: 0 for state, _label in Order.PAYMENT_STATE_CHOICES}
        for row in selected_orders.values('payment_state').annotate(count=Count('id')):
            payment_counts_map[row['payment_state']] = row['count']
        payment_chart_data = {
            'labels': [label for _state, label in Order.PAYMENT_STATE_CHOICES],
            'values': [payment_counts_map[state] for state, _label in Order.PAYMENT_STATE_CHOICES],
        }

        category_data = list(OrderItem.objects.filter(
            order__created_at__range=(selected_start_at, selected_end_at)
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
            category_chart = plot(fig, output_type='div', include_plotlyjs=True)
        else:
            category_chart = format_html(
                '<div style="padding: 2rem; text-align: center; color: #9ca3af;">No category data available for the selected period.</div>'
            )

        repeat_customers = selected_orders.exclude(email='').values('email').annotate(order_count=Count('id')).filter(order_count__gt=1).count()
        top_products = OrderItem.objects.filter(order__created_at__range=(selected_start_at, selected_end_at)).values('product_name').annotate(
            total_quantity=Sum('quantity')
        ).order_by('-total_quantity')[:5]

        context = {**self.each_context(request),
            'today_orders': today_summary['order_count'],
            'week_orders': week_summary['order_count'],
            'month_orders': month_summary['order_count'],
            'today_revenue': today_summary['revenue'],
            'today_profit': today_summary['profit'],
            'week_revenue': week_summary['revenue'],
            'week_profit': week_summary['profit'],
            'month_revenue': month_summary['revenue'],
            'month_profit': month_summary['profit'],
            'selected_orders': selected_summary['order_count'],
            'selected_revenue': selected_summary['revenue'],
            'selected_profit': selected_summary['profit'],
            'selected_range': selected_range['selected_range'],
            'selected_start_date': selected_start.isoformat(),
            'selected_end_date': selected_end.isoformat(),
            'paid_orders': selected_summary['paid_orders'],
            'pending_orders': selected_summary['pending_orders'],
            'payment_chart_data': payment_chart_data,
            'financial_chart_data': financial_chart_data,
            'category_chart': category_chart,
            'avg_order_value': selected_summary['avg_order_value'],
            'repeat_customers': repeat_customers,
            'total_customers': selected_summary['total_customers'],
            'delivered_orders': selected_summary['delivered_orders'],
            'cancelled_orders': selected_summary['cancelled_orders'],
            'top_products': top_products,
            'title': 'Advanced Analytics Dashboard'
        }

        return TemplateResponse(request, 'admin/analytics_dashboard.html', context)

    def index(self, request, extra_context=None):
        """Enhanced dashboard — AH1: adds yesterday comparison + pending orders count,
        and consolidates multiple same-model queries into single aggregates."""
        extra_context = extra_context or {}

        check_and_create_alerts()

        today     = timezone.localdate()
        yesterday = today - timedelta(days=1)

        # Two _summarize_orders calls; each issues 2 queries (aggregate + profit).
        today_summary     = _summarize_orders(today, today)
        # AH1: yesterday summary enables trend indicators in the template.
        yesterday_summary = _summarize_orders(yesterday, yesterday)

        overview_range = _resolve_date_range(request, default_days=14)
        overview_summary = _summarize_orders(
            overview_range['start_date'],
            overview_range['end_date'],
        )
        overview_chart_data = _build_financial_chart_data(
            overview_range['start_date'],
            overview_range['end_date'],
        )

        # AH1: 3 separate Product queries → 1 aggregate (saves 2 DB round-trips).
        product_stats = Product.objects.aggregate(
            total=Count('id'),
            out_of_stock=Count('id', filter=Q(stock=0)),
            low_stock=Count('id', filter=Q(stock__gt=0, stock__lt=10)),
        )

        # AH1: 2 separate NewsletterSubscriber queries → 1 aggregate (saves 1 DB hit).
        subscriber_stats = NewsletterSubscriber.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )

        # AH1: total pending orders needing attention (all-time, not just today).
        # Uses the existing index on payment_state (via is_read analogy — no migration needed).
        total_pending = Order.objects.filter(
            payment_state__in=FOLLOW_UP_PAYMENT_STATES
        ).count()

        # Two AdminAlert queries: one for the badge count, one for the 5-item list.
        unread_alerts = AdminAlert.objects.filter(is_read=False).count()
        recent_alerts = (
            AdminAlert.objects
            .filter(is_read=False)
            .select_related('product', 'order')
            .order_by('-severity', '-created_at')[:5]
        )

        extra_context.update({
            # Today
            'today_orders':   today_summary['order_count'],
            'today_revenue':  today_summary['revenue'],
            'today_profit':   today_summary['profit'],
            # AH1: Yesterday — used for trend arrows in template.
            'yesterday_orders':  yesterday_summary['order_count'],
            'yesterday_revenue': yesterday_summary['revenue'],
            'yesterday_profit':  yesterday_summary['profit'],
            # AH1: All-time pending orders count.
            'total_pending': total_pending,
            # Products (from single aggregate)
            'total_products': product_stats['total'],
            'out_of_stock':   product_stats['out_of_stock'],
            'low_stock':      product_stats['low_stock'],
            # Subscribers (from single aggregate)
            'total_subscribers':  subscriber_stats['total'],
            'active_subscribers': subscriber_stats['active'],
            # Alerts
            'unread_alerts': unread_alerts,
            'recent_alerts': recent_alerts,
            # Overview chart
            'overview_orders':  overview_summary['order_count'],
            'overview_revenue': overview_summary['revenue'],
            'overview_profit':  overview_summary['profit'],
            'overview_range':      overview_range['selected_range'],
            'overview_start_date': overview_range['start_date'].isoformat(),
            'overview_end_date':   overview_range['end_date'].isoformat(),
            'overview_chart_data': overview_chart_data,
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
    
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_subcategory_count=Count('subcategories', distinct=True))

    def subcategories_count(self, obj):
        count = obj._subcategory_count
        return format_html('<span style="background-color: #ff6f91; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>', count)
    subcategories_count.short_description = "Subcategories"
    subcategories_count.admin_order_field = '_subcategory_count'


class SubCategoryAdmin(ModelAdmin):
    list_display = ('name','category', 'slug')
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'category__name')
    list_select_related = ['category']
    list_per_page = 25


class FeatureReasonAdmin(ModelAdmin):
    list_display = ('Reason',)
    list_per_page = 25


# ========================
# PRODUCT ADMIN (WITH EXPORTS)
# ========================

class ProductAdminForm(forms.ModelForm):

    long_description = forms.CharField(
        widget=CKEditor5Widget(config_name='default'),
        required=False,
        label="Long description",
    )

    class Meta:
        model = Product
        fields = '__all__'


class ProductColorImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        active_colors = set()
        image_count = 0

        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                continue

            color = form.cleaned_data.get('color')
            image = form.cleaned_data.get('image')
            if not image:
                if color:
                    raise ValidationError('Add an image for each color row, or leave the row empty.')
                continue

            image_count += 1

            if color:
                color_key = color.pk
                if color_key in active_colors:
                    raise ValidationError('Each color can only have one image per product.')

                active_colors.add(color_key)

        if image_count < 1:
            raise ValidationError('Add at least one product image.')


class ProductColorImageInline(TabularInline):
    model = ProductColorImage
    formset = ProductColorImageInlineFormSet
    extra = 1
    fields = ('color', 'image',)
    verbose_name = "Product Image"
    verbose_name_plural = "Product Images"


class ProductAdmin(ExportActionMixin, ModelAdmin):
    resource_class = ProductResource
    form = ProductAdminForm
    
    list_display = ('product_name_with_image', 'get_price_display', 'stock_status', 'subcategory', 'is_featured', 'get_colors', 'created_at')
    search_fields = ('name', 'description', 'long_description', 'slug')
    list_filter = ('tags', 'subcategory', 'is_featured', 'size', 'created_at')
    filter_horizontal = ('tags',)
    inlines = [ProductColorImageInline]
    readonly_fields = ('slug', 'discount_percentage_display', 'created_at')
    list_per_page = 25
    list_display_links = ['product_name_with_image']
    ordering = ['-created_at']
    show_full_result_count = False
    save_as = True
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Product Details', {
            'fields': ('long_description',)
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'buying_price', 'discount_price', 'discount_percentage_display', 'stock')
        }),
        ('Categorization', {
            'fields': ('subcategory', 'tags')
        }),
        ('Product Attributes', {
            'fields': ('size',)
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

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('color_images__color')
    
    def product_name_with_image(self, obj):
        primary_image = obj.get_primary_image()
        if primary_image:
            return format_html(
                '<div style="display: flex; align-items: center;"><img src="{}" style="height: 40px; border-radius: 5px; margin-right: 10px;" /><strong>{}</strong></div>',
                primary_image.url, obj.name
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
        color_names = obj.get_available_color_names()
        return ', '.join(color_names) if color_names else '-'
    get_colors.short_description = "Color"
    
    # Image preview removed — Unfold admin provides an automatic preview
    
    def discount_percentage_display(self, obj):
        return format_html('<strong>{}</strong>', f"{float(obj.discount_percentage):.1f}%") if getattr(obj, "discount_percentage", 0) and obj.discount_percentage > 0 else "-"
    discount_percentage_display.short_description = "Discount %"
    
    def save_model(self, request, obj, form, change):
        if obj.subcategory:
            obj.category = obj.subcategory.category
        super().save_model(request, obj, form, change)


class ReviewAdmin(ModelAdmin):
    list_display = ('product', 'user', 'get_rating_display', 'comment_preview', 'created_at')
    list_display_links = ['product']
    list_filter = ('rating', 'created_at', 'product')
    search_fields = ('product__name', 'user__username', 'comment')
    readonly_fields = ('created_at',)
    list_per_page = 25
    ordering = ['-created_at']
    list_select_related = ['product', 'user']

    def comment_preview(self, obj):
        if len(obj.comment) > 60:
            return obj.comment[:60] + '\u2026'
        return obj.comment
    comment_preview.short_description = "Comment"

    def get_rating_display(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span style="font-size: 18px;">{}</span> <strong>{}/5</strong>', stars, obj.rating)
    get_rating_display.short_description = "Rating"
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class ColorAdmin(ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    list_per_page = 25

    def products_count(self, obj):
        count = Product.objects.filter(
            Q(color=obj) | Q(color_images__color=obj)
        ).distinct().count()
        return format_html(f'<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{count}</span>')
    products_count.short_description = "Products"


class SizeAdmin(ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_product_count=Count('product', distinct=True))

    def products_count(self, obj):
        count = obj._product_count
        return format_html('<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>', count)
    products_count.short_description = "Products"
    products_count.admin_order_field = '_product_count'


class TagAdmin(ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_product_count=Count('products', distinct=True))

    def products_count(self, obj):
        count = obj._product_count
        return format_html('<span style="background-color: #667bc6; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>', count)
    products_count.short_description = "Products"
    products_count.admin_order_field = '_product_count'


class ProductColorImageAdmin(ModelAdmin):
    list_display = ('product', 'color', 'image_preview')
    list_filter = ('color', 'product')
    search_fields = ('product__name', 'color__name')
    list_select_related = ['product', 'color']
    list_per_page = 25

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 40px; border-radius: 3px;" />', obj.image.url)
        return '-'
    image_preview.short_description = "Image"


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
    list_display_links = ['email']
    list_per_page = 50
    
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
    readonly_fields = ['product', 'product_name', 'product_color', 'product_price', 'quantity']
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
    readonly_fields = ['user', 'order_number','full_name', 'email', 'phone', 'original_price', 'shipping_cost',
                      'discount_amount', 'total_price', 'coupon', 'inventory_restored_at',
                      'coupon_usage_released_at', 'created_at', 'updated_at',
                      'billing_address', 'shipping_address','notes']
    list_select_related = ['user', 'shipping_address', 'billing_address', 'coupon']
    date_hierarchy = 'created_at'
    list_per_page = 25
    list_display_links = ['order_id']
    ordering = ['-created_at']
    show_full_result_count = False
    actions_on_bottom = True

    fieldsets = [
        ('Order Information', {
            'fields': ['order_status', 'user', 'order_number', 'full_name', 'email', 'phone', 'coupon', 'created_at', 'updated_at']
        }),
        ('Addresses', {
            'fields': ['shipping_address', 'billing_address']
        }),
        ('Payment Information', {
            'fields': ['payment_method', 'payment_state', 'transaction_id', 'sender_number']
        }),
        ('Manual Payment Workflow', {
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

        try:
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

        except ValidationError as exc:
            msg = _validation_error_message(exc)
            self.message_user(request, f"Could not update order: {msg}", level=messages.ERROR)
            # Signal response_change to skip the normal success redirect/message.
            request._order_lifecycle_failed = True

    def response_change(self, request, obj):
        """Redirect back to the change form (no success message) when a lifecycle
        transition failed during save_model."""
        if getattr(request, '_order_lifecycle_failed', False):
            return HttpResponseRedirect(request.path)
        return super().response_change(request, obj)

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
    list_per_page = 25

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
    list_select_related = ['user']
    list_per_page = 25

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
    list_per_page = 25
    ordering = ['-valid_to']

    fieldsets = (
        ("Coupon Information", {
            'fields': ('code', 'is_active', 'is_valid_display')
        }),
        ("Discount Details", {
            'fields': ('discount_amount', 'discount_percent', 'max_discount_amount', 'minimum_order_value')
        }),
        ("Validity", {
            'fields': ('valid_from', 'valid_to', 'usage_limit', 'max_uses_per_phone', 'used_count')
        }),
    )
    
    def discount_display(self, obj):
        if obj.discount_amount:
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
    list_per_page = 25
    actions = ['mark_all_as_read']

    def mark_all_as_read(self, request, queryset):
        updated = queryset.filter(is_read=False).update(is_read=True, read_by=request.user)
        self.message_user(request, f'{updated} alert(s) marked as read.')
    mark_all_as_read.short_description = "Mark selected alerts as read"

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

class SliderAdmin(ModelAdmin):
    change_list_template = 'admin/iwm/slider/change_list.html'

    list_display = ('slide_preview', 'title', 'subtitle', 'order', 'status_badge')
    list_display_links = ['slide_preview', 'title']
    search_fields = ('title', 'subtitle')
    list_filter = ('is_active',)
    list_per_page = 25

    fieldsets = (
        ('Slide Image', {
            'fields': ('image',)
        }),
        ('Content', {
            'fields': ('title', 'subtitle', 'button_text', 'button_url')
        }),
        ('Display', {
            'fields': ('order', 'is_active')
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'reorder/',
                self.admin_site.admin_view(self.reorder_view),
                name='slider-reorder',
            ),
        ]
        return custom_urls + urls

    def reorder_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
        try:
            data = json.loads(request.body)
            order_list = data.get('order', [])
            with transaction.atomic():
                for item in order_list:
                    Slider.objects.filter(pk=item['id']).update(order=item['order'])
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['slides'] = Slider.objects.all().order_by('order')
        return super().changelist_view(request, extra_context=extra_context)

    def slide_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height: 50px; width: 90px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return "-"
    slide_preview.short_description = "Preview"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#d4edda; color:#155724; padding:4px 10px; border-radius:20px; font-weight:bold;">ACTIVE</span>'
            )
        return format_html(
            '<span style="background:#f8d7da; color:#721c24; padding:4px 10px; border-radius:20px; font-weight:bold;">INACTIVE</span>'
        )
    status_badge.short_description = "Status"


class PromoBannerAdmin(ModelAdmin):
    list_display = (
        'title_1',
        'title_2',
        'status_badge',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'title_1',
        'title_2',
        'description',
    )

    list_per_page = 25

    fieldsets = (
        ('Banner Content', {
            'fields': (
                'title_1',
                'title_2',
                'description',
                'image',
            )
        }),

        ('Status', {
            'fields': (
                'is_active',
            )
        }),
    )

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#d4edda; color:#155724; '
                'padding:5px 10px; border-radius:20px; '
                'font-weight:bold;">ACTIVE</span>'
            )

        return format_html(
            '<span style="background:#f8d7da; color:#721c24; '
            'padding:5px 10px; border-radius:20px; '
            'font-weight:bold;">INACTIVE</span>'
        )

    status_badge.short_description = "Status"
    
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
admin_site.register(Tag, TagAdmin)
admin_site.register(ProductColorImage, ProductColorImageAdmin)
admin_site.register(NewsletterSubscriber, NewsletterSubscriberAdmin)
admin_site.register(Order, OrderAdmin)
admin_site.register(OrderItem, OrderItemAdmin)
admin_site.register(Address, AddressAdmin)
admin_site.register(Coupon, CouponAdmin)
admin_site.register(AdminAlert, AdminAlertAdmin)
admin_site.register(PromoBanner, PromoBannerAdmin)
admin_site.register(Slider, SliderAdmin)
