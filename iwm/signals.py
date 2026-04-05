from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, UserVerification


@receiver(post_save, sender=User)
def ensure_user_profile_and_verification(sender, instance, created, **kwargs):
    if not created:
        return

    UserProfile.objects.get_or_create(user=instance)
    UserVerification.objects.get_or_create(
        user=instance,
        defaults={'verified': instance.is_active},
    )
