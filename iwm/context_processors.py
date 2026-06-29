from django.conf import settings

def google_tag_manager(request):
    """
    Context processor to add the Google Tag Manager ID to the template context.
    """
    return {
        'GOOGLE_TAG_MANAGER_ID': getattr(settings, 'GOOGLE_TAG_MANAGER_ID', '')
    }
