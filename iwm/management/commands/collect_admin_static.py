from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Display information about admin customization'

    def handle(self, *args, **options):
        self.stdout.write(
            'Admin customization files have been created successfully.\n'
            'Make sure to run "python manage.py collectstatic" to deploy static files.'
        )