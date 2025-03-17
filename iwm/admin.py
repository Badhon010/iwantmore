from django.contrib import admin
from .models import Product, Review, Tag, MoreImages, NewsletterSubscriber, Category, SubCategory, FeatureReason
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

# Register Product model with custom admin - FIXED ORDER
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("admin/custom.css",)}
        js = ("admin/custom.js",)

    list_display = ('name', 'price', 'discount_price', 'subcategory', 'is_featured', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('price', 'discount_price', 'tags', 'subcategory', 'is_featured')
    filter_horizontal = ('tags',)
    inlines = [MoreImagesInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'price', 'discount_price', 'image', 'stock')
        }),
        ('Categorization', {
            'fields': ('subcategory', 'tags')  # এখানে 'category' বাদ দেওয়া হয়েছে
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
