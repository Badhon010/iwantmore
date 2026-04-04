from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Review, UserProfile, UserVerification, NewsletterSubscriber,Category, SubCategory, Coupon, Address, Order, OrderItem, Color, Size, Brand
from .forms import ReviewForm
from django.db.models import Q,Avg, Case, When, DecimalField, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
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
from django.db import models
from django.utils.text import slugify
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
import time
from django.utils import timezone
import google.generativeai as genai
import os
import traceback
import textwrap
from decouple import config

def rd(request):
    return redirect('home')

def _404_view(request, exception):
    return render(request, '404.html', status=404)

def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(is_featured=True).order_by('-created_at')[:8]  # show latest 8 featured products
    brands= Brand.objects.all()
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'brands': brands
    }
    return render(request, 'home.html', context)

def shop(request):
    products = Product.objects.all()
    for product in products:
        # Calculate average rating from reviews
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        int_part = int(avg_rating)
        frac = avg_rating - int_part

        # Set the average rating and half-star flag
        if frac < 0.3:
            product.avg_rating = int_part
            product.half = False
        elif frac < 0.7:
            product.avg_rating = int_part
            product.half = True
        else:
            product.avg_rating = int_part + 1
            product.half = False

        # Calculate stars for display
        product.full_stars = range(product.avg_rating)
        product.empty_stars = range(5 - product.avg_rating - (1 if product.half else 0))

    return render(request, 'shop.html', {'products': products,'categories': Category.objects.all(),'colors': Color.objects.all(),'sizes': Size.objects.all(),'brands': Brand.objects.all() })


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
        except Exception as e:
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
    product = get_object_or_404(Product, slug=slug)
    
    # Get related products from the same category, excluding the current product
    related_by_category = Product.objects.filter(category=product.category).exclude(id=product.id)
    
    # Get related products with similar tags
    product_tags = product.tags.all()
    related_by_tags = Product.objects.filter(tags__in=product_tags).exclude(id=product.id).distinct()
    
    # Combine both querysets and remove duplicates
    related_products = list(related_by_category)
    for item in related_by_tags:
        if item not in related_products:
            related_products.append(item)
    
    # Limit to 4 related products
    related_products = related_products[:4]
    
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
    
    products = Product.objects.all()

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
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:  # newest
        products = products.order_by('-created_at')

    # Calculate average ratings for display
    for product in products:
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
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
            
        # Calculate stars for display
        product.full_stars = range(product.avg_rating)
        product.empty_stars = range(5 - product.avg_rating - (1 if product.half else 0))

    context = {
        "products": products,
        "query": query,
        "min_price": min_price,
        "max_price": max_price,
        "category": category,
        "stock": stock,
        "sort": sort,
        "discount": discount,
        "featured": featured,
        "categories": Category.objects.all(),
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
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_active = False
            user.save()

            UserProfile.objects.create(user=user)
            UserVerification.objects.create(user=user)

            current_site = get_current_site(request)
            mail_subject = 'Activate your account'
            message = render_to_string('acc_active.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            email_message = EmailMultiAlternatives(mail_subject, message, 'your_email@example.com', [email])
            email_message.attach_alternative(message, "text/html")
            email_message.send()

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
        user.save()
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
            except Exception as e:
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

from django.db import transaction


def checkout(request):
    if request.method != 'POST':
        return render(request, 'checkout.html')

    cart = request.session.get('cart', [])
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    # Form data
    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    address_line1 = request.POST.get('address_line1', '').strip()
    address_line2 = request.POST.get('address_line2', '').strip()
    city = request.POST.get('city', '').strip()
    state = request.POST.get('state', '').strip()
    postal_code = request.POST.get('postal_code', '').strip()
    country = request.POST.get('country', 'Bangladesh').strip()
    payment_method = request.POST.get('payment_method', 'cash_on_delivery').strip()

    # 🆕 Manual payment fields
    sender_number = request.POST.get('sender_number', '').strip()
    trx_id = request.POST.get('trx_id', '').strip()

    shipping_cost = float(request.session.get('shipping_cost', 0))

    # Calculate total
    subtotal = sum(int(i.get('quantity', 1)) * float(i.get('price', 0)) for i in cart)
    total = subtotal + shipping_cost

    try:
        with transaction.atomic():
            shipping_address = Address.objects.create(
                user=request.user if request.user.is_authenticated else None,
                address_type='shipping',
                full_name=full_name,
                phone=phone,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                postal_code=postal_code,
                state=state,
                country=country,
            )

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=full_name,
                email=email,
                phone=phone,
                shipping_address=shipping_address,
                billing_address=shipping_address,
                total_price=total,
                original_price=subtotal,
                shipping_cost=shipping_cost,
                discount_amount=0,
                order_status='pending',
                payment_method=payment_method,
                payment_status=False,  # unpaid by default
                transaction_id=trx_id,
            )

            # 🆕 Save sender number (if you added field in model)
            if hasattr(order, 'sender_number'):
                order.sender_number = sender_number
                order.save(update_fields=['sender_number'])

            # Create order items
            for entry in cart:
                product = None
                try:
                    product = Product.objects.select_for_update().get(id=entry.get('id'))
                except:
                    pass

                qty = int(entry.get('quantity', 1))
                price = float(entry.get('price', 0))

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=entry.get('name', ''),
                    product_price=price,
                    quantity=qty,
                )

                if product:
                    product.stock = max(0, product.stock - qty)
                    product.save(update_fields=['stock'])

            # Clear session
            request.session.pop('cart', None)
            request.session.pop('shipping_cost', None)
            request.session.pop('coupon_id', None)

            if not request.user.is_authenticated:
                request.session['guest_order_id'] = str(order.id)

            return redirect(f"{reverse('order_confirmation')}?order_id={order.id}")

    except Exception as e:
        messages.error(request, f'Error placing order: {str(e)}')
        return redirect('cart')

def order_confirmation(request):
    # Accept ?order_id=<id> or show the latest order for authenticated users
    order_id = request.GET.get('order_id')

    order = None
    if order_id:
        try:
            order = Order.objects.select_related('shipping_address', 'billing_address', 'user').prefetch_related('items__product').get(id=order_id)
            # Security: allow if the order belongs to the logged in user
            if request.user.is_authenticated:
                if order.user and order.user != request.user:
                    order = None
            else:
                # allow guest only if session has the guest_order_id
                if request.session.get('guest_order_id') != str(order_id):
                    order = None
        except Order.DoesNotExist:
            order = None
    else:
        if request.user.is_authenticated:
            order = Order.objects.filter(user=request.user).order_by('-created_at').first()

    items = []
    if order:
        for it in order.items.all():
            try:
                line_total = it.product_price * it.quantity
            except Exception:
                # fallback to numeric multiplication
                line_total = float(it.product_price) * int(it.quantity)
            items.append({
                'product_name': it.product_name,
                'product_price': it.product_price,
                'quantity': it.quantity,
                'line_total': line_total,
                'product': it.product,
            })

    return render(request, 'order_confirmation.html', {'order': order, 'items': items})

def apply_coupon(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        code = request.POST.get('coupon_code')
        
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
            
            # Check if coupon is expired
            if coupon.valid_to and coupon.valid_to < timezone.now():
                return JsonResponse({'status': 'error', 'message': 'This coupon has expired'})
            
            # Store coupon in session
            request.session['coupon_id'] = coupon.id
            
            # Apply the correct discount (amount or percentage)
            if coupon.discount_amount > 0:
                request.session['discount'] = float(coupon.discount_amount)
            else:
                request.session['discount'] = float(coupon.discount_percent)
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Coupon applied successfully', 
                'discount': request.session['discount'],
                'discount_type': 'amount' if coupon.discount_amount > 0 else 'percent'
            })
            
        except Coupon.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid coupon code'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@require_POST
def place_order(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})

    # Extract data
    personal_info = data.get('personal_info', {})
    shipping_address_data = data.get('shipping_address', {})
    billing_address_data = data.get('billing_address', {})
    payment_method = data.get('payment_method', 'cash_on_delivery')
    payment_details = data.get('payment_details', {})
    items = data.get('items', [])
    additional_notes = data.get('additional_notes', '')
    totals = data.get('totals', {})

    if not items:
        return JsonResponse({'status': 'error', 'message': 'Cart is empty'})

    # 🔍 Stock validation
    for item in items:
        try:
            product = Product.objects.get(id=item.get('id'))
            if product.stock < int(item.get('quantity', 1)):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Not enough stock for {product.name}'
                })
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found'
            })

    try:
        with transaction.atomic():

            # ✅ Create shipping address
            shipping_address = Address.objects.create(
                user=request.user if request.user.is_authenticated else None,
                address_type='shipping',
                full_name=shipping_address_data.get('full_name', personal_info.get('full_name', '')),
                phone=personal_info.get('phone', ''),
                address_line1=shipping_address_data.get('address_line1', ''),
                address_line2=shipping_address_data.get('address_line2', ''),
                city=shipping_address_data.get('city', ''),
                postal_code=shipping_address_data.get('postal_code', ''),
                state=shipping_address_data.get('state', ''),
                country=shipping_address_data.get('country', 'Bangladesh')
            )

            # ✅ Billing address
            if data.get('same_billing_address', True):
                billing_address = shipping_address
            else:
                billing_address = Address.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    address_type='billing',
                    full_name=billing_address_data.get('full_name', personal_info.get('full_name', '')),
                    phone=personal_info.get('phone', ''),
                    address_line1=billing_address_data.get('address_line1', ''),
                    address_line2=billing_address_data.get('address_line2', ''),
                    city=billing_address_data.get('city', ''),
                    postal_code=billing_address_data.get('postal_code', ''),
                    state=billing_address_data.get('state', ''),
                    country=billing_address_data.get('country', 'Bangladesh')
                )

            # 💰 Pricing
            total_price = float(totals.get('total', 0))
            original_price = float(totals.get('subtotal', 0))
            shipping_cost = float(totals.get('shipping', 0))
            discount_amount = float(totals.get('discount', 0))

            # ✅ Create order (ALL payments pending)
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=personal_info.get('full_name', ''),
                email=personal_info.get('email', ''),
                phone=personal_info.get('phone', ''),
                shipping_address=shipping_address,
                billing_address=billing_address,
                total_price=total_price,
                original_price=original_price,
                shipping_cost=shipping_cost,
                discount_amount=discount_amount,
                order_status='pending',
                payment_method=payment_method,
                payment_status=False,  # ❗ ALWAYS False initially
                notes=additional_notes
            )

            # 🧾 Manual Payment Logic (FIXED)
            order.sender_number = ''
            order.transaction_id = ''
            order.delivery_charge_paid = False
            order.delivery_payment_method = None
            order.delivery_transaction_id = ''

            if payment_method == 'cash_on_delivery':
                # User will pay delivery charge later via bKash/Nagad
                order.delivery_payment_method = payment_details.get('delivery_payment_method', '')
                order.delivery_transaction_id = payment_details.get('delivery_transaction_id', '')

            elif payment_method in ['bkash', 'nagad']:
                # User may provide details but still NOT confirmed
                order.sender_number = payment_details.get('sender_number', '')
                order.transaction_id = payment_details.get('transaction_id', '')

            order.save()

            # 📦 Create order items + update stock
            for item in items:
                product = None
                try:
                    product = Product.objects.select_for_update().get(id=item.get('id'))
                except Product.DoesNotExist:
                    pass

                quantity = int(item.get('quantity', 1))
                price = float(item.get('price', 0))

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=item.get('name', ''),
                    product_price=price,
                    quantity=quantity
                )

                if product:
                    product.stock = max(0, product.stock - quantity)
                    product.save(update_fields=['stock'])

            # 🧹 Clear session
            request.session.pop('coupon_id', None)
            request.session.pop('discount', None)

            return JsonResponse({
                'status': 'success',
                'message': 'Order placed successfully. We will contact you on Messenger to confirm.',
                'order_id': order.id
            })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error processing order: {str(e)}'
        })

@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Security check: ensure the order belongs to the current user
    if order.user != request.user:
        messages.error(request, "You don't have permission to view this order.")
        return redirect('my_orders')
        
    return render(request, 'track_order.html', {'order': order})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Security check: ensure the order belongs to the current user
    if order.user != request.user:
        messages.error(request, "You don't have permission to cancel this order.")
        return redirect('my_orders')
    
    # Only allow cancellation if order is in 'pending' status
    if order.order_status != 'pending':
        messages.error(request, "Only pending orders can be cancelled.")
        return redirect('my_orders')
    
    # Update order status to cancelled
    order.order_status = 'cancelled'
    order.save()
    
    messages.success(request, f"Order #{order.id} has been cancelled successfully.")
    return redirect('my_orders')

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})

@login_required
def order_count(request):
    active_statuses = ['pending', 'processing', 'shipped']
    count = request.user.orders.filter(order_status__in=active_statuses).count()
    return JsonResponse({'count': count})

# Gemini API integration for AI features
genai.configure(api_key=config("GEMINI_API_KEY"))
GEMINI_API_KEY = config("GEMINI_API_KEY", default=None)# Configure Gemini API once

def build_site_context(request):
    parts = []

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

        # Recent/active products
        products = Product.objects.filter(is_active=True).order_by("-updated_at")[:10]
        if products:
            parts.append("\nProducts:")
            for p in products:
                parts.append(
                    f"- {getattr(p, 'name', 'N/A')} (${getattr(p, 'price', 'N/A')}) "
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
        return JsonResponse({"reply": "Server is missing GEMINI_API_KEY."}, status=500)

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
        You are a helpful e-commerce support assistant for this website.
        Answer using the provided CONTEXT and be concise. If something is not in the context,
        use general retail knowledge but never invent specific store policies.
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
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"reply": f"Error: {str(e)}"}, status=500)