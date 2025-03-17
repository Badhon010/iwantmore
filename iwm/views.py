from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Review, UserProfile, UserVerification, NewsletterSubscriber,Category
from .forms import ReviewForm
from django.db.models import Q,Avg
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

def rd(request):
    return redirect('home')

def _404_view(request, exception):
    return render(request, '404.html', status=404)

def home(request):
    return render(request, 'home.html', {'categories': Category.objects.all()})

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

    return render(request, 'shop.html', {'products': products})


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
    return render(request, 'product.html', {'product': product})

def search_view(request):
    query = request.GET.get("q", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    products = Product.objects.all()

    if query:
        # Split the query into individual words
        query_words = query.split()
        # Build a Q object to search each word in name, description, or tags
        query_filter = Q()
        for word in query_words:
            query_filter |= Q(name__icontains=word)
            query_filter |= Q(description__icontains=word)
            query_filter |= Q(tags__name__icontains=word)
        products = products.filter(query_filter).distinct()

    if min_price:
        try:
            min_price_val = float(min_price)
            products = products.filter(price__gte=min_price_val)
        except ValueError:
            pass

    if max_price:
        try:
            max_price_val = float(max_price)
            products = products.filter(price__lte=max_price_val)
        except ValueError:
            pass

    context = {
        "products": products,
        "query": query,
        "min_price": min_price,
        "max_price": max_price,
    }
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
        
        # Combine the results in the desired order without duplicates
        combined_products = []
        seen_ids = set()
        
        for group in (name_matches, tag_matches, desc_matches):
            for product in group:
                if product.id not in seen_ids:
                    combined_products.append(product)
                    seen_ids.add(product.id)
                # Stop if we already have 6 suggestions
                if len(combined_products) == 6:
                    break
            if len(combined_products) == 6:
                break

        # Create suggestions with URLs using the id from your URL config.
        suggestions = [
            {
                "name": product.name,
                "url": reverse("product_detail", kwargs={"id": product.id}),
            }
            for product in combined_products
        ]
    
    return JsonResponse(suggestions, safe=False)

@login_required
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

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
            return redirect('product_detail', id=product.id)

    return render(request, 'product_details.html', {'product': product})

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
            message = render_to_string('emails/acc_active.html', {
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