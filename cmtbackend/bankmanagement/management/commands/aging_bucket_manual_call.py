# cmtbackend/bankmanagement/management/commands/update_aging_bucket.py
from django.core.management.base import BaseCommand
from bankmanagement.agingbucket import update_aging_bucket

class Command(BaseCommand):
    help = 'Manually call the update_aging_bucket function to update the aging bucket for Cash Tracker Report.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting the update_aging_bucket function...'))
        update_aging_bucket()
        self.stdout.write(self.style.SUCCESS('update_aging_bucket function completed successfully.'))