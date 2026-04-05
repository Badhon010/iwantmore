from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from iwm.models import UserVerification

class Command(BaseCommand):
    help = 'Deletes unverified users who registered more than 24 hours ago.'

    def handle(self, *args, **options):
        # Set the grace period to 24 hours
        grace_period = timedelta(hours=24)
        time_limit = timezone.now() - grace_period

        # Only remove accounts that are still inactive and explicitly unverified.
        unverified_records = UserVerification.objects.select_related('user').filter(
            verification_sent_at__lte=time_limit,
            verified=False,
            user__is_active=False,
        )

        for record in unverified_records:
            user = record.user
            self.stdout.write(f"Deleting unverified user: {user.username}")
            user.delete()  # This will delete the associated user as well

        self.stdout.write("Finished deleting unverified users.")
