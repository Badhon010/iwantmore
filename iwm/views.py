from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Review, UserProfile, UserVerification, NewsletterSubscriber,Category, SubCategory, Coupon, Address, Order, OrderItem, Color, Size, Brand
from .forms import ReviewForm
from django.db.models import Q, Avg, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from .tokens import account_activation_token
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db import models, IntegrityError, transaction
from django.utils.text import slugify
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
import time
from django.utils import timezone
import google.generativeai as genai
import os
import logging
import textwrap
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from decouple import config

logger = logging.getLogger(__name__)

def rd(request):
    return redirect('home')

def _404_view(request, exception):
    return render(request, '404.html', status=404)


def _500_view(request):
    return render(request, '500.html', status=500)


def _base_product_queryset():
    return Product.objects.select_related(
        'category',
        'subcategory',
        'color',
        'size',
        'brand',
        'feature_reason',
    ).prefetch_related(
        'tags',
    ).annotate(
        avg_rating_value=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True),
    )


def _apply_product_rating_display(products):
    for product in products:
        avg_rating = float(product.avg_rating_value or 0)
        int_part = int(avg_rating)
        frac = avg_rating - int_part

        if frac < 0.3:
            product.avg_rating = int_part
            product.half = False
        elif frac < 0.7:
            product.avg_rating = int_part
            product.half = True
        else:
            product.avg_rating = int_part + 1
            product.half = False

        product.full_stars = range(product.avg_rating)
        product.empty_stars = range(5 - product.avg_rating - (1 if product.half else 0))


def _paginate_queryset(request, queryset, per_page=16):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop('page', None)
    pagination_query = query_params.urlencode()

    return page_obj, pagination_query

def home(request):
    categories = Category.objects.prefetch_related('subcategories').all()
    featured_products = _base_product_queryset().filter(is_featured=True).order_by('-created_at')[:8]
    _apply_product_rating_display(featured_products)
    brands = Brand.objects.all()
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'brands': brands
    }
    return render(request, 'home.html', context)

def shop(request):
    products = _base_product_queryset().order_by('-created_at')
    paginated_products, pagination_query = _paginate_queryset(request, products)
    _apply_product_rating_display(paginated_products)

    return render(request, 'shop.html', {
        'products': paginated_products,
        'pagination_query': pagination_query,
        'pagination_total_count': paginated_products.paginator.count,
        'categories': Category.objects.prefetch_related('subcategories').all(),
        'colors': Color.objects.all(),
        'sizes': Size.objects.all(),
        'brands': Brand.objects.all(),
    })


def about(request):
    return render(request, 'about.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Send email
        try:
            send_mail(
                f'Contact Form: {subject}',
                f'Name: {name}\nEmail: {email}\n\nMessage:\n{message}',
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],  # Send to admin email
                fail_silently=False,
            )
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
        except Exception:
            logger.exception('Contact form email send failed.')
            messages.error(request, 'Sorry, there was an error sending your message. Please try again later.')
        
        return redirect('contact')
    
    return render(request, 'contact.html')

def services(request):
    return render(request, 'services.html')

def profile(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = None 
    return render(request, 'profile.html',{'profile':profile})
def edit_profile(request):
    # Ensure the user is logged in before allowing them to edit their profile
    if not request.user.is_authenticated:
        return redirect('login')  # Redirect to login page if the user is not authenticated

    profile = request.user.userprofile

    if request.method == 'POST':
        profile.phone_number = request.POST.get('phone_number')
        profile.location = request.POST.get('location')
        profile.bio = request.POST.get('bio')
        
        # Handling Profile Picture upload
        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES['profile_picture']
        
        profile.save()
        return redirect('profile')  # Redirect to the profile page after saving the changes

    # If it's a GET request, just render the form
    return render(request, 'edit_profile.html', {'profile': profile})

def product_detail(request, slug):
    product = get_object_or_404(
        _base_product_queryset(),
        slug=slug,
    )
    
    # Get related products from the same category, excluding the current product
    related_by_category = list(
        _base_product_queryset().filter(category=product.category).exclude(id=product.id)[:4]
    )
    
    # Get related products with similar tags
    product_tags = product.tags.all()
    related_by_tags = list(
        _base_product_queryset().filter(tags__in=product_tags).exclude(id=product.id).distinct()[:4]
    )
    
    # Combine both querysets and remove duplicates
    related_products = list(related_by_category)
    for item in related_by_tags:
        if item not in related_products:
            related_products.append(item)
    
    # Limit to 4 related products
    related_products = related_products[:4]
    _apply_product_rating_display([product, *related_products])
    
    context = {
        'product': product,
        'related_products': related_products
    }
    
    return render(request, 'product.html', context)

def search_view(request):
    query = request.GET.get("q", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    category = request.GET.get("category", "").strip()
    stock = request.GET.get("stock", "all")
    sort = request.GET.get("sort", "newest")
    discount = request.GET.get("discount", "false") == "true"
    featured = request.GET.get("featured", "false") == "true"
    selected_color = request.GET.get("color", "").strip()
    selected_size = request.GET.get("size", "").strip()
    selected_brand = request.GET.get("brand", "").strip()
    
    products = _base_product_queryset()

    # Apply search filter
    if query:
        query_words = query.split()
        query_filter = Q()
        for word in query_words:
            query_filter |= Q(name__icontains=word)
            query_filter |= Q(description__icontains=word)
            query_filter |= Q(tags__name__icontains=word)
            query_filter |= Q(category__name__icontains=word)
            query_filter |= Q(subcategory__name__icontains=word)
        products = products.filter(query_filter).distinct()

    # Apply category filter
    if category:
        # First try to find a category with this slug
        category_obj = Category.objects.filter(slug=category).first()
        if category_obj:
            products = products.filter(category=category_obj)
        else:
            # If not found as category, try to find as subcategory
            subcategory_obj = SubCategory.objects.filter(slug=category).first()
            if subcategory_obj:
                products = products.filter(subcategory=subcategory_obj)

    # Apply price range filter
    if min_price:
        try:
            min_price_val = float(min_price)
            # Filter by effective price - consider discount_price when available
            min_price_filter = Q(
                discount_price__isnull=False, 
                discount_price__gte=min_price_val
            ) | Q(
                discount_price__isnull=True,
                price__gte=min_price_val
            )
            products = products.filter(min_price_filter)
        except ValueError:
            pass

    if max_price:
        try:
            max_price_val = float(max_price)
            # Filter by effective price - consider discount_price when available
            max_price_filter = Q(
                discount_price__isnull=False, 
                discount_price__lte=max_price_val
            ) | Q(
                discount_price__isnull=True,
                price__lte=max_price_val
            )
            products = products.filter(max_price_filter)
        except ValueError:
            pass

    # Apply stock filter
    if stock == "in-stock":
        products = products.filter(stock__gt=0)
    elif stock == "out-of-stock":
        products = products.filter(stock=0)

    # Apply discount filter
    if discount:
        products = products.filter(discount_price__isnull=False)

    # Apply featured filter
    if featured:
        products = products.filter(is_featured=True)

    # Apply color filter
    if selected_color:
        products = products.filter(color__name__iexact=selected_color)

    # Apply size filter
    if selected_size:
        products = products.filter(size__name__iexact=selected_size)

    # Apply brand filter
    if selected_brand:
        products = products.filter(brand__name__iexact=selected_brand)
    
    # Apply sorting
    if sort == "price-low":
        products = products.annotate(
            effective_price=models.Case(
                models.When(discount_price__isnull=False, then='discount_price'),
                default='price',
                output_field=models.DecimalField()
            )
        ).order_by('effective_price')
    elif sort == "price-high":
        products = products.annotate(
            effective_price=models.Case(
                models.When(discount_price__isnull=False, then='discount_price'),
                default='price',
                output_field=models.DecimalField()
            )
        ).order_by('-effective_price')
    elif sort == "rating":
        products = products.order_by('-avg_rating_value', '-review_count', '-created_at')
    else:  # newest
        products = products.order_by('-created_at')

    products, pagination_query = _paginate_queryset(request, products)
    _apply_product_rating_display(products)

    context = {
        "products": products,
        "pagination_query": pagination_query,
        "pagination_total_count": products.paginator.count,
        "query": query,
        "min_price": min_price,
        "max_price": max_price,
        "category": category,
        "stock": stock,
        "sort": sort,
        "discount": discount,
        "featured": featured,
        "categories": Category.objects.prefetch_related('subcategories').all(),
        "colors": Color.objects.all(),
        "sizes": Size.objects.all(),
        "brands": Brand.objects.all(),
        "selected_color": selected_color,
        "selected_size": selected_size,
        "selected_brand": selected_brand,
    }
    
    # If it's an AJAX request, return only the product grid
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "shop.html", context)
    
    return render(request, "shop.html", context)

def autocomplete_suggestions(request):
    query = request.GET.get("q", "").strip()
    suggestions = []
    
    if query:
        # 1. Search in product name
        name_matches = list(Product.objects.filter(name__icontains=query).distinct())
        
        # 2. Search in tags
        tag_matches = list(Product.objects.filter(tags__name__icontains=query).distinct())
        
        # 3. Search in description for all words
        words = query.split()
        q_desc = Q()
        for word in words:
            q_desc &= Q(description__icontains=word)
        desc_matches = list(Product.objects.filter(q_desc).distinct())
        
        # 4. Search in categories
        category_matches = list(Category.objects.filter(name__icontains=query).distinct())
        
        # Combine the results in the desired order without duplicates
        combined_products = []
        seen_ids = set()
        
        for group in (name_matches, tag_matches, desc_matches):
            for product in group:
                if product.id not in seen_ids:
                    combined_products.append(product)
                    seen_ids.add(product.id)
                # Stop if we already have 5 suggestions
                if len(combined_products) == 5:
                    break
            if len(combined_products) == 5:
                break

        # Create product suggestions with detailed information
        suggestions = [
            {
                "name": product.name,
                "url": reverse("product_detail", kwargs={"slug": product.slug}),
                "category": product.category.name if product.category else "Product",
                "price": float(product.price),
                "type": "product",
                "match_type": "product" if product in name_matches else "tag" if product in tag_matches else "description"
            }
            for product in combined_products
        ]
        
        # Add category suggestions
        if len(suggestions) < 6:
            for category in category_matches[:2]:  # Limit to 2 categories
                suggestions.append({
                    "name": f"Category: {category.name}",
                    "url": f"{reverse('search')}?category={category.slug}",
                    "type": "category",
                    "match_type": "category"
                })
                
        # Add tag suggestions if space
        if len(suggestions) < 6:
            tag_query = Q(name__icontains=query)
            tags = Product.tags.through.objects.filter(
                tag__name__icontains=query
            ).values('tag__name').distinct()[:2]
            
            for tag_entry in tags:
                tag_name = tag_entry['tag__name']
                if any(s.get('name') == f"Tag: {tag_name}" for s in suggestions):
                    continue
                suggestions.append({
                    "name": f"Tag: {tag_name}",
                    "url": f"{reverse('search')}?q={tag_name}",
                    "type": "tag",
                    "match_type": "tag"
                })
    
    return JsonResponse(suggestions, safe=False)

@login_required
def submit_review(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)

    if request.method == 'POST':
        review_text = request.POST.get('review')
        rating = request.POST.get('rating')

        if review_text and rating:
            review = Review.objects.create(
                product=product,
                user=request.user,
                comment=review_text,
                rating=rating
            )
            review.save()
            return redirect('product_detail', slug=product.slug)

    return render(request, 'product.html', {'product': product})

def logout_view(request):
    logout(request)
    return redirect('home')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if User.objects.filter(username=username).exists():
            error = f"This username '{username}' already exists, choose another one"
            return render(request, 'signup.html', {'error': error, 'username': username, 'email': email})
        elif User.objects.filter(email=email).exists():
            error = 'This email is already registered, please login'
            return render(request, 'signup.html', {'error': error, 'username': username, 'email': email})
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                return render(request, 'signup.html', {
                    'error': ' '.join(exc.messages),
                    'username': username,
                    'email': email,
                })

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False,
            )

            current_site = get_current_site(request)
            mail_subject = 'Activate your account'
            message = render_to_string('acc_active.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            email_message = EmailMultiAlternatives(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            email_message.attach_alternative(message, "text/html")

            try:
                email_message.send()
            except Exception:
                logger.exception('Account activation email failed to send for user %s.', user.pk)
                error = 'Your account was created, but we could not send the verification email right now. Please contact support.'
                return render(request, 'signup.html', {'error': error, 'username': username, 'email': email})

            alert_message = 'A verification email has been sent. Please check your email to verify your account.'
            return render(request, 'signup.html', {'alert_message': alert_message})
    
    return render(request, 'signup.html', {'error': ''})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        UserVerification.objects.update_or_create(
            user=user,
            defaults={'verified': True},
        )
        UserProfile.objects.get_or_create(user=user)
        # Specify the backend explicitly
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('complete_profile')
    else:
        return redirect('home')


@login_required
def complete_profile(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        profile_picture = request.FILES.get('profile_picture')

        user = request.user
        name_parts = full_name.split(maxsplit=1)
        user.first_name = name_parts[0] if len(name_parts) > 0 else ""
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""

        user.save()

        if phone_number or profile_picture:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = phone_number
            if profile_picture:
                profile.profile_picture = profile_picture
            profile.save()

        return redirect('home')

    return render(request, 'complete_profile.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            user_obj = User.objects.get(email=email)
            if not user_obj.is_active:
                error = 'Please verify your email before logging in.'
                return render(request, 'login.html', {'error': error, 'email': email})
            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                error = 'Invalid email or password'
                return render(request, 'login.html', {'error': error, 'email': email})
        except User.DoesNotExist:
            error = 'No account found with this email'
            return render(request, 'login.html', {'error': error, 'email': email})
    return render(request, 'login.html', {'error': ''})

def faq(request):
    """
    Render the FAQ page with categorized questions and answers.
    """
    return render(request, 'faq.html')

@require_POST
def subscribe_newsletter(request):
    """Handle newsletter subscription requests."""
    if request.method == 'POST':
        email = request.POST.get('email', '')
        source = request.POST.get('source', '')
        
        if not email:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Email is required'})
            messages.error(request, 'Email address is required.')
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        
        # Check if already subscribed
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'source': source, 'is_active': True}
        )
        
        if not created and subscriber.is_active:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'info', 'message': 'You are already subscribed to our newsletter.'})
            messages.info(request, 'You are already subscribed to our newsletter.')
        else:
            if not created:
                # Reactivate previously unsubscribed user
                subscriber.is_active = True
                subscriber.save()
            
            # Send confirmation email to subscriber
            try:
                send_mail(
                    'Thank you for subscribing to I Want More Newsletter',
                    f'Dear Subscriber,\n\nThank you for subscribing to the I Want More newsletter. '
                    f'You will now receive the latest updates, offers, and news from us.\n\n'
                    f'If you have any questions, please contact us at iwantmore.bd999@gmail.com.\n\n'
                    f'Best regards,\nThe I Want More Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                
                # Send notification to admin
                admin_email = settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else 'iwantmore.bd999@gmail.com'
                send_mail(
                    'New Newsletter Subscription',
                    f'A new user has subscribed to the newsletter:\n\nEmail: {email}\nSource: {source or "Not specified"}\nDate: {subscriber.subscribed_at}',
                    settings.DEFAULT_FROM_EMAIL,
                    [admin_email],
                    fail_silently=False,
                )
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': 'Thank you for subscribing to our newsletter!'})
                messages.success(request, 'Thank you for subscribing to our newsletter!')
            except Exception:
                logger.exception('Newsletter subscription email flow failed.')
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'There was an error processing your subscription. Please try again later.'})
                messages.error(request, 'There was an error processing your subscription. Please try again later.')
        
        # Redirect back to the referring page
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    # If not POST, redirect to home
    return redirect('home')

def cart(request):
    return render(request, 'cart.html')

def wishlist(request):
    return render(request, 'wishlist.html')


MONEY_QUANTIZER = Decimal('0.01')
INSIDE_DHAKA_SHIPPING = Decimal('80.00')
OUTSIDE_DHAKA_SHIPPING = Decimal('150.00')
ORDER_ACCESS_SESSION_KEY = 'authorized_order_ids'


def _to_money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal('0.00')
    return amount.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def _normalize_payment_method(method):
    normalized = (method or '').strip().lower()
    if normalized in {'cash_on_delivery', 'cash-on-delivery', 'cod'}:
        return 'cash_on_delivery'
    if normalized in {'bkash', 'nagad'}:
        return normalized
    return None


def _normalize_phone(phone_number):
    digits = ''.join(ch for ch in (phone_number or '') if ch.isdigit())
    if len(digits) >= 11:
        return digits[-11:]
    return digits


def _normalized_contact(contact_value):
    return (contact_value or '').strip().lower()


def _order_contact_matches(order, contact_value):
    normalized_contact = _normalized_contact(contact_value)
    if not normalized_contact:
        return False

    if (order.email or '').strip().lower() == normalized_contact:
        return True

    normalized_phone = _normalize_phone(contact_value)
    return bool(normalized_phone and _normalize_phone(order.phone) == normalized_phone)


def _authorized_order_ids(request):
    raw_ids = request.session.get(ORDER_ACCESS_SESSION_KEY, [])
    authorized_ids = []

    if not isinstance(raw_ids, list):
        return authorized_ids

    for raw_id in raw_ids:
        try:
            authorized_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    return authorized_ids


def _grant_order_access(request, order_ids):
    authorized_ids = list(dict.fromkeys(_authorized_order_ids(request) + [int(order_id) for order_id in order_ids]))
    request.session[ORDER_ACCESS_SESSION_KEY] = authorized_ids[:50]


def _lookup_orders_by_contact_and_pin(contact_value, access_pin, order_id=None):
    normalized_contact = _normalized_contact(contact_value)
    normalized_phone = _normalize_phone(contact_value)
    if not normalized_contact or not access_pin:
        return []

    queryset = Order.objects.select_related('shipping_address', 'billing_address', 'user').prefetch_related('items__product').order_by('-created_at')

    if order_id:
        try:
            queryset = queryset.filter(id=int(order_id))
        except (TypeError, ValueError):
            return []

    candidates = []
    seen_ids = set()

    for order in queryset.filter(email__iexact=normalized_contact):
        if order.id not in seen_ids:
            candidates.append(order)
            seen_ids.add(order.id)

    if normalized_phone:
        phone_hint = normalized_phone[-4:] if len(normalized_phone) >= 4 else normalized_phone
        for order in queryset.filter(phone__icontains=phone_hint):
            if order.id not in seen_ids:
                candidates.append(order)
                seen_ids.add(order.id)

    matches = []
    for order in candidates:
        if _order_contact_matches(order, contact_value) and order.check_access_pin(access_pin):
            matches.append(order)

    return matches


def _resolve_checkout_items(raw_items):
    if not isinstance(raw_items, list):
        raise ValueError('Invalid cart data.')

    quantities = {}
    ordered_product_ids = []

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError('Invalid cart item.')

        try:
            product_id = int(raw_item.get('id'))
            quantity = int(raw_item.get('quantity', 1))
        except (TypeError, ValueError):
            raise ValueError('Invalid cart item.')

        if product_id <= 0 or quantity <= 0:
            raise ValueError('Invalid cart item.')

        if product_id not in quantities:
            ordered_product_ids.append(product_id)
            quantities[product_id] = 0

        quantities[product_id] += quantity

    if not ordered_product_ids:
        raise ValueError('Cart is empty.')

    products = Product.objects.in_bulk(ordered_product_ids)
    missing_product_ids = [product_id for product_id in ordered_product_ids if product_id not in products]
    if missing_product_ids:
        raise ValueError('Some products are no longer available.')

    resolved_items = []
    subtotal = Decimal('0.00')

    for product_id in ordered_product_ids:
        product = products[product_id]
        quantity = quantities[product_id]
        unit_price = _to_money(product.get_final_price())
        line_total = _to_money(unit_price * quantity)
        resolved_items.append({
            'product_id': product.id,
            'product': product,
            'product_name': product.name,
            'quantity': quantity,
            'unit_price': unit_price,
            'line_total': line_total,
        })
        subtotal += line_total

    return resolved_items, _to_money(subtotal)


def _shipping_cost_for_state(state):
    normalized_state = (state or '').strip().lower()
    if 'dhaka' in normalized_state:
        return INSIDE_DHAKA_SHIPPING
    return OUTSIDE_DHAKA_SHIPPING


def _session_coupon(request):
    coupon_id = request.session.get('coupon_id')
    if not coupon_id:
        return None

    try:
        coupon = Coupon.objects.get(pk=coupon_id, is_active=True)
    except Coupon.DoesNotExist:
        request.session.pop('coupon_id', None)
        return None

    if not coupon.is_valid:
        request.session.pop('coupon_id', None)
        return None

    return coupon


def _validate_coupon(coupon, subtotal):
    if coupon is None:
        return False, 'Invalid coupon code.'

    if not coupon.is_valid:
        return False, 'This coupon is no longer valid.'

    minimum_order_value = _to_money(coupon.minimum_order_value)
    if minimum_order_value and subtotal < minimum_order_value:
        return False, f'Minimum order amount for this coupon is à§³{minimum_order_value:.2f}.'

    return True, ''


def _coupon_discount_amount(coupon, subtotal):
    if not coupon:
        return Decimal('0.00')

    if coupon.discount_amount > 0:
        discount_amount = _to_money(coupon.discount_amount)
    else:
        discount_amount = _to_money(subtotal * Decimal(coupon.discount_percent) / Decimal('100'))

    return min(discount_amount, subtotal)


def _build_pricing_summary(resolved_items, shipping_state, coupon=None):
    subtotal = _to_money(sum(item['line_total'] for item in resolved_items))
    shipping_cost = _shipping_cost_for_state(shipping_state) if resolved_items else Decimal('0.00')
    discount_amount = _coupon_discount_amount(coupon, subtotal)
    total = _to_money(subtotal + shipping_cost - discount_amount)

    return {
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'discount_amount': discount_amount,
        'total': total,
    }


def _serialize_checkout_items(resolved_items):
    return [
        {
            'id': item['product_id'],
            'name': item['product_name'],
            'quantity': item['quantity'],
            'unit_price': float(item['unit_price']),
            'line_total': float(item['line_total']),
            'image': item['product'].image.url if item['product'].image else '',
        }
        for item in resolved_items
    ]


def _serialize_pricing_summary(pricing):
    return {
        'subtotal': float(pricing['subtotal']),
        'shipping': float(pricing['shipping_cost']),
        'discount': float(pricing['discount_amount']),
        'total': float(pricing['total']),
    }

def checkout(request):
    return render(request, 'checkout.html')

@require_POST
def checkout_totals(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    shipping_state = data.get('shipping_state', '')
    coupon_code = (data.get('coupon_code') or '').strip()
    clear_coupon = bool(data.get('clear_coupon'))

    try:
        resolved_items, subtotal = _resolve_checkout_items(data.get('items', []))
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)

    coupon = None
    message = ''

    if clear_coupon:
        request.session.pop('coupon_id', None)
    elif coupon_code:
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
        except Coupon.DoesNotExist:
            request.session.pop('coupon_id', None)
            return JsonResponse({'status': 'error', 'message': 'Invalid coupon code'}, status=400)

        is_valid, coupon_message = _validate_coupon(coupon, subtotal)
        if not is_valid:
            request.session.pop('coupon_id', None)
            return JsonResponse({'status': 'error', 'message': coupon_message}, status=400)

        request.session['coupon_id'] = coupon.id
        message = 'Coupon applied successfully.'
    else:
        coupon = _session_coupon(request)
        if coupon:
            is_valid, coupon_message = _validate_coupon(coupon, subtotal)
            if not is_valid:
                request.session.pop('coupon_id', None)
                coupon = None
                message = coupon_message

    pricing = _build_pricing_summary(resolved_items, shipping_state, coupon)

    return JsonResponse({
        'status': 'success',
        'items': _serialize_checkout_items(resolved_items),
        'totals': _serialize_pricing_summary(pricing),
        'coupon': {
            'code': coupon.code,
            'discount_amount': float(pricing['discount_amount']),
        } if coupon else None,
        'message': message,
    })


def order_confirmation(request):
    order_id = request.GET.get('order_id')

    order = None
    if order_id:
        try:
            order = Order.objects.select_related(
                'shipping_address',
                'billing_address',
                'user',
            ).prefetch_related('items__product').get(id=order_id)
            has_account_access = request.user.is_authenticated and order.user == request.user
            has_lookup_access = request.session.get('guest_order_id') == str(order_id) or order.id in _authorized_order_ids(request)
            if not has_account_access and not has_lookup_access:
                order = None
        except Order.DoesNotExist:
            order = None
    elif request.user.is_authenticated:
        order = Order.objects.filter(user=request.user).order_by('-created_at').first()

    items = []
    if order:
        for item in order.items.all():
            try:
                line_total = item.product_price * item.quantity
            except Exception:
                line_total = float(item.product_price) * int(item.quantity)

            items.append({
                'product_name': item.product_name,
                'product_price': item.product_price,
                'quantity': item.quantity,
                'line_total': line_total,
                'product': item.product,
            })

    return render(request, 'order_confirmation.html', {'order': order, 'items': items})


def apply_coupon(request):
    if request.method != 'POST' or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    code = (request.POST.get('coupon_code') or '').strip()
    shipping_state = request.POST.get('shipping_state', '')
    items_payload = request.POST.get('items_json', '[]')

    try:
        raw_items = json.loads(items_payload)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid cart data'}, status=400)

    try:
        resolved_items, subtotal = _resolve_checkout_items(raw_items)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)

    try:
        coupon = Coupon.objects.get(code__iexact=code, is_active=True)
    except Coupon.DoesNotExist:
        request.session.pop('coupon_id', None)
        return JsonResponse({'status': 'error', 'message': 'Invalid coupon code'}, status=400)

    is_valid, coupon_message = _validate_coupon(coupon, subtotal)
    if not is_valid:
        request.session.pop('coupon_id', None)
        return JsonResponse({'status': 'error', 'message': coupon_message}, status=400)

    request.session['coupon_id'] = coupon.id
    pricing = _build_pricing_summary(resolved_items, shipping_state, coupon)

    return JsonResponse({
        'status': 'success',
        'message': 'Coupon applied successfully.',
        'items': _serialize_checkout_items(resolved_items),
        'totals': _serialize_pricing_summary(pricing),
        'coupon': {
            'code': coupon.code,
            'discount_amount': float(pricing['discount_amount']),
        },
    })


@require_POST
def place_order(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    personal_info = data.get('personal_info') or {}
    shipping_address_data = data.get('shipping_address') or {}
    billing_address_data = data.get('billing_address') or {}
    payment_details = data.get('payment_details') or {}
    raw_items = data.get('items') or []
    additional_notes = (data.get('additional_notes') or '').strip()
    same_billing_address = bool(data.get('same_billing_address', True))
    payment_method = _normalize_payment_method(data.get('payment_method'))
    idempotency_key = (data.get('idempotency_key') or '').strip()
    access_pin = (data.get('access_pin') or personal_info.get('access_pin') or '').strip()

    if not idempotency_key:
        return JsonResponse({'status': 'error', 'message': 'Missing idempotency key.'}, status=400)

    if not access_pin.isdigit() or not 4 <= len(access_pin) <= 8:
        return JsonResponse({'status': 'error', 'message': 'Order access PIN must be 4 to 8 digits.'}, status=400)

    existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
    if existing_order:
        if not request.user.is_authenticated and existing_order.user is None:
            request.session['guest_order_id'] = str(existing_order.id)
        _grant_order_access(request, [existing_order.id])
        return JsonResponse({
            'status': 'success',
            'message': 'Order already received. We will continue with the same order.',
            'order_id': existing_order.id,
        })

    if payment_method is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid payment method.'}, status=400)

    try:
        requested_items, _ = _resolve_checkout_items(raw_items)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)

    full_name = (personal_info.get('full_name') or '').strip()
    email = (personal_info.get('email') or '').strip()
    phone = (personal_info.get('phone') or '').strip()
    shipping_full_name = (shipping_address_data.get('full_name') or full_name).strip()
    shipping_address_line1 = (shipping_address_data.get('address_line1') or '').strip()
    shipping_address_line2 = (shipping_address_data.get('address_line2') or '').strip()
    shipping_city = (shipping_address_data.get('city') or '').strip()
    shipping_postal_code = (shipping_address_data.get('postal_code') or '').strip()
    shipping_state = (shipping_address_data.get('state') or '').strip()
    shipping_country = (shipping_address_data.get('country') or 'Bangladesh').strip()

    required_values = [
        (full_name, 'Full name'),
        (email, 'Email'),
        (phone, 'Phone number'),
        (shipping_full_name, 'Shipping full name'),
        (shipping_address_line1, 'Shipping address'),
        (shipping_city, 'Shipping city'),
        (shipping_postal_code, 'Shipping postal code'),
        (shipping_state, 'Shipping state'),
        (shipping_country, 'Shipping country'),
    ]

    for value, label in required_values:
        if not value:
            return JsonResponse({'status': 'error', 'message': f'{label} is required.'}, status=400)

    billing_full_name = (billing_address_data.get('full_name') or full_name).strip()
    billing_address_line1 = (billing_address_data.get('address_line1') or '').strip()
    billing_address_line2 = (billing_address_data.get('address_line2') or '').strip()
    billing_city = (billing_address_data.get('city') or '').strip()
    billing_postal_code = (billing_address_data.get('postal_code') or '').strip()
    billing_state = (billing_address_data.get('state') or '').strip()
    billing_country = (billing_address_data.get('country') or 'Bangladesh').strip()

    if not same_billing_address:
        billing_required_values = [
            (billing_full_name, 'Billing full name'),
            (billing_address_line1, 'Billing address'),
            (billing_city, 'Billing city'),
            (billing_postal_code, 'Billing postal code'),
            (billing_state, 'Billing state'),
            (billing_country, 'Billing country'),
        ]
        for value, label in billing_required_values:
            if not value:
                return JsonResponse({'status': 'error', 'message': f'{label} is required.'}, status=400)

    sender_number = (payment_details.get('sender_number') or '').strip()
    transaction_id = (payment_details.get('transaction_id') or '').strip()
    delivery_payment_method = _normalize_payment_method(payment_details.get('delivery_payment_method'))
    delivery_transaction_id = (payment_details.get('delivery_transaction_id') or '').strip()

    if payment_method in {'bkash', 'nagad'} and not sender_number:
        return JsonResponse({'status': 'error', 'message': 'Sender number is required for manual payment.'}, status=400)

    if delivery_payment_method == 'cash_on_delivery':
        delivery_payment_method = None

    if delivery_payment_method not in {None, 'bkash', 'nagad'}:
        return JsonResponse({'status': 'error', 'message': 'Invalid delivery payment method.'}, status=400)

    coupon = _session_coupon(request)
    payment_state = 'payment_submitted' if payment_method in {'bkash', 'nagad'} else 'awaiting_payment'

    try:
        with transaction.atomic():
            existing_order = Order.objects.select_for_update().filter(idempotency_key=idempotency_key).first()
            if existing_order:
                if not request.user.is_authenticated and existing_order.user is None:
                    request.session['guest_order_id'] = str(existing_order.id)
                _grant_order_access(request, [existing_order.id])
                return JsonResponse({
                    'status': 'success',
                    'message': 'Order already received. We will continue with the same order.',
                    'order_id': existing_order.id,
                })

            requested_quantities = {
                item['product_id']: item['quantity']
                for item in requested_items
            }
            locked_products = Product.objects.select_for_update().filter(
                id__in=requested_quantities.keys()
            ).order_by('id')
            product_map = {product.id: product for product in locked_products}

            if len(product_map) != len(requested_quantities):
                return JsonResponse({'status': 'error', 'message': 'Some products are no longer available.'}, status=400)

            locked_items = []
            for item in requested_items:
                product = product_map[item['product_id']]
                quantity = requested_quantities[product.id]

                if product.stock < quantity:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Not enough stock for {product.name}.',
                    }, status=400)

                unit_price = _to_money(product.get_final_price())
                line_total = _to_money(unit_price * quantity)
                locked_items.append({
                    'product': product,
                    'product_name': product.name,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'line_total': line_total,
                })

            subtotal = _to_money(sum(item['line_total'] for item in locked_items))
            if coupon:
                is_valid, _coupon_message = _validate_coupon(coupon, subtotal)
                if not is_valid:
                    request.session.pop('coupon_id', None)
                    coupon = None

            pricing = _build_pricing_summary(locked_items, shipping_state, coupon)

            shipping_address = Address.objects.create(
                user=request.user if request.user.is_authenticated else None,
                address_type='shipping',
                full_name=shipping_full_name,
                phone=phone,
                address_line1=shipping_address_line1,
                address_line2=shipping_address_line2,
                city=shipping_city,
                postal_code=shipping_postal_code,
                state=shipping_state,
                country=shipping_country,
            )

            if same_billing_address:
                billing_address = shipping_address
            else:
                billing_address = Address.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    address_type='billing',
                    full_name=billing_full_name,
                    phone=phone,
                    address_line1=billing_address_line1,
                    address_line2=billing_address_line2,
                    city=billing_city,
                    postal_code=billing_postal_code,
                    state=billing_state,
                    country=billing_country,
                )

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                idempotency_key=idempotency_key,
                full_name=full_name,
                email=email,
                phone=phone,
                shipping_address=shipping_address,
                billing_address=billing_address,
                total_price=pricing['total'],
                original_price=pricing['subtotal'],
                shipping_cost=pricing['shipping_cost'],
                discount_amount=pricing['discount_amount'],
                order_status='pending',
                payment_method=payment_method,
                sender_number=sender_number if payment_method in {'bkash', 'nagad'} else None,
                transaction_id=transaction_id if payment_method in {'bkash', 'nagad'} else None,
                payment_state=payment_state,
                delivery_charge_paid=False,
                delivery_payment_method=delivery_payment_method if payment_method == 'cash_on_delivery' else None,
                delivery_transaction_id=delivery_transaction_id if payment_method == 'cash_on_delivery' else None,
                notes=additional_notes,
            )
            order.set_access_pin(access_pin)
            order.save(update_fields=['access_pin_hash'])

            for item in locked_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_name=item['product_name'],
                    product_price=item['unit_price'],
                    quantity=item['quantity'],
                )
                item['product'].stock -= item['quantity']
                item['product'].save(update_fields=['stock'])

            if coupon:
                Coupon.objects.filter(pk=coupon.pk).update(used_count=models.F('used_count') + 1)

            request.session.pop('coupon_id', None)
            request.session.pop('discount', None)

            if not request.user.is_authenticated:
                request.session['guest_order_id'] = str(order.id)
            _grant_order_access(request, [order.id])

            return JsonResponse({
                'status': 'success',
                'message': 'Order placed successfully. We will contact you to confirm payment and delivery.',
                'order_id': order.id,
            })
    except IntegrityError:
        existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing_order:
            if not request.user.is_authenticated and existing_order.user is None:
                request.session['guest_order_id'] = str(existing_order.id)
            _grant_order_access(request, [existing_order.id])
            return JsonResponse({
                'status': 'success',
                'message': 'Order already received. We will continue with the same order.',
                'order_id': existing_order.id,
            })

        return JsonResponse({'status': 'error', 'message': 'Could not process your order. Please try again.'}, status=500)
    except Exception:
        logger.exception('Order placement failed.')
        return JsonResponse({
            'status': 'error',
            'message': 'Could not process your order right now. Please try again.',
        }, status=500)

def track_order(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('shipping_address', 'billing_address', 'user').prefetch_related('items__product'),
        id=order_id,
    )

    has_account_access = request.user.is_authenticated and order.user == request.user
    has_lookup_access = order.id in _authorized_order_ids(request)

    if not has_account_access and not has_lookup_access:
        messages.error(request, "You don't have permission to view this order.")
        return redirect('my_orders')

    return render(request, 'track_order.html', {'order': order})


@login_required
@require_POST
def cancel_order(request, order_id):
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().prefetch_related('items__product'),
            id=order_id,
        )

        if order.user != request.user:
            messages.error(request, "You don't have permission to cancel this order.")
            return redirect('my_orders')

        if order.order_status != 'pending':
            messages.error(request, "Only pending orders can be cancelled.")
            return redirect('my_orders')

        for item in order.items.all():
            if item.product:
                item.product.stock += item.quantity
                item.product.save(update_fields=['stock'])

        order.order_status = 'cancelled'
        order.save(update_fields=['order_status', 'updated_at'])

    messages.success(request, f"Order #{order.id} has been cancelled successfully.")
    return redirect('my_orders')

def my_orders(request):
    account_orders = Order.objects.none()
    if request.user.is_authenticated:
        account_orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')

    lookup_contact = ''
    lookup_pin = ''
    lookup_order_id = ''
    lookup_orders = Order.objects.none()
    authorized_ids = _authorized_order_ids(request)

    if authorized_ids:
        lookup_orders = Order.objects.select_related('shipping_address', 'billing_address', 'user').prefetch_related('items__product').filter(
            id__in=authorized_ids
        ).order_by('-created_at')

    if request.method == 'POST':
        lookup_contact = (request.POST.get('contact') or '').strip()
        lookup_pin = (request.POST.get('access_pin') or '').strip()
        lookup_order_id = (request.POST.get('order_id') or '').strip()

        if not lookup_contact or not lookup_pin:
            messages.error(request, 'Enter the email or phone number and the order PIN you used at checkout.')
        elif not lookup_pin.isdigit() or not 4 <= len(lookup_pin) <= 8:
            messages.error(request, 'Order PIN must be 4 to 8 digits.')
        else:
            matched_orders = _lookup_orders_by_contact_and_pin(lookup_contact, lookup_pin, lookup_order_id)
            if matched_orders:
                _grant_order_access(request, [order.id for order in matched_orders])
                lookup_orders = Order.objects.select_related('shipping_address', 'billing_address', 'user').prefetch_related('items__product').filter(
                    id__in=[order.id for order in matched_orders]
                ).order_by('-created_at')
            else:
                lookup_orders = Order.objects.none()
                messages.error(request, 'We could not find any orders with those details.')

    return render(request, 'my_orders.html', {
        'orders': account_orders,
        'lookup_orders': lookup_orders,
        'lookup_contact': lookup_contact,
        'lookup_pin': lookup_pin,
        'lookup_order_id': lookup_order_id,
        'show_lookup_results': bool(lookup_contact or authorized_ids),
    })

def order_count(request):
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})

    active_statuses = ['pending', 'processing', 'shipped']
    count = request.user.orders.filter(order_status__in=active_statuses).count()
    return JsonResponse({'count': count})

# Gemini API integration for AI features
GEMINI_API_KEY = (config("GEMINI_API_KEY", default="") or "").strip()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def build_site_context(request):
    parts = []

    # --- Website Name ---
    parts.append("Website Name: I Want More (IWM)")

    # --- Basic site/domain ---
    try:
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current(request).domain
        parts.append(f"Site domain: {domain}")
    except Exception:
        pass

    # --- Products & Categories ---
    try:
        from .models import Product, Category, SubCategory, Brand, Color, Size, Coupon, Review, OrderItem

        # Recent products
        products = Product.objects.all().order_by("-created_at")[:10]
        if products:
            parts.append("\nProducts:")
            for p in products:
                parts.append(
                    f"- {getattr(p, 'name', 'N/A')} (Taka {getattr(p, 'price', 'N/A')}) "
                    f"[Category: {getattr(p.category, 'name', 'N/A')}, "
                    f"SubCategory: {getattr(p.subcategory, 'name', 'N/A')}, "
                    f"Brand: {getattr(p.brand, 'name', 'N/A')}, "
                    f"Color: {getattr(p.color, 'name', 'N/A')}, "
                    f"Size: {getattr(p.size, 'name', 'N/A')}]"
                )

        # Categories & Subcategories
        categories = Category.objects.all()[:5]
        if categories:
            parts.append("\nCategories:")
            for c in categories:
                parts.append(f"- {c.name}")
                subcats = SubCategory.objects.filter(category=c)[:5]
                for sc in subcats:
                    parts.append(f"  - {sc.name}")

        # Brands
        brands = Brand.objects.all()[:5]
        if brands:
            parts.append("\nBrands:")
            for b in brands:
                parts.append(f"- {b.name}")

        # Colors & Sizes
        colors = Color.objects.all()[:5]
        if colors:
            parts.append("\nColors: " + ", ".join([c.name for c in colors]))
        sizes = Size.objects.all()[:5]
        if sizes:
            parts.append("\nSizes: " + ", ".join([s.name for s in sizes]))

        # Popular products (by sold quantity)
        popular = OrderItem.objects.values("product__name").annotate(count=Count("id")).order_by("-count")[:5]
        if popular:
            parts.append("\nPopular Products:")
            for p in popular:
                parts.append(f"- {p['product__name']} (sold {p['count']} times)")

        # Coupons
        coupons = Coupon.objects.all()[:5]
        if coupons:
            parts.append("\nCoupons:")
            for c in coupons:
                parts.append(f"- {c.code}: {getattr(c, 'discount', 'N/A')}% off")

        # Recent Reviews
        reviews = Review.objects.select_related("product").order_by("-created_at")[:5]
        if reviews:
            parts.append("\nRecent Reviews:")
            for r in reviews:
                parts.append(f"- {r.product.name}: {r.text[:100]}")  # first 100 chars
    except Exception:
        pass

    # --- Optional: User info ---
    if request.user.is_authenticated:
        parts.append(f"\nUser: {request.user.get_username()} (authenticated)")

    # --- Limit context length ---
    context_text = "\n".join(parts)
    return context_text[:8000]  # truncate to avoid token overflow

def format_history(history):
    # history: [{'role': 'user'|'assistant', 'text': '...'}]
    lines = []
    for turn in history[-20:]:
        r = "User" if turn.get("role") == "user" else "Assistant"
        t = turn.get("text", "").strip()
        if t:
            lines.append(f"{r}: {t}")
    return "\n".join(lines)

@require_POST
def gemini_chat(request):
    if not GEMINI_API_KEY:
        return JsonResponse({"reply": "Chat support is temporarily unavailable."}, status=503)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"reply": "Invalid JSON"}, status=400)

    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return JsonResponse({"reply": "Please send a message."}, status=400)

    # Build site context
    site_context = build_site_context(request)
    history_txt = format_history(history)

    system_instruction = textwrap.dedent("""
        You are a helpful e-commerce support assistant for "I Want More" website.
        The website name is "I Want More" (also known as IWM).
        Answer using the provided CONTEXT and be concise. If something is not in the context,
        use general retail knowledge but never invent specific store policies.
        Always refer to the website as "I Want More" when mentioning the store name.
    """)

    user_prompt = f"""
    CONTEXT:
    {site_context}

    CHAT HISTORY:
    {history_txt}

    USER QUESTION:
    {message}
    """

    try:
        model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            system_instruction=system_instruction.strip()
        )
        result = model.generate_content(user_prompt.strip())
        reply = getattr(result, "text", None) or "Sorry, I couldn't generate a response."
        return JsonResponse({"reply": reply})
    except Exception:
        logger.exception("Gemini chat request failed.")
        return JsonResponse({"reply": "Chat support is temporarily unavailable. Please try again later."}, status=500)
