from django.core.management.base import BaseCommand
from documents.policy_calculation import PolicyDatabaseUpdater
import logging
from django.db import transaction
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates all policy calculations in the database'

    def add_arguments(self, parser):
        # Optional reporting date argument
        parser.add_argument(
            '--date',
            type=str,
            help='Reporting date in YYYY-MM-DD format. Defaults to current date if not provided.',
        )

        # Optional dry run flag
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run calculations without saving to database',
        )

    def handle(self, *args, **options):
        try:
            # Parse reporting date if provided
            reporting_date = None
            if options['date']:
                try:
                    reporting_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                except ValueError:
                    self.stderr.write(
                        self.style.ERROR('Invalid date format. Please use YYYY-MM-DD')
                    )
                    return

            # Initialize the updater
            updater = PolicyDatabaseUpdater()
            if reporting_date:
                updater.reporting_date = reporting_date

            # Start the process
            self.stdout.write(
                self.style.SUCCESS('Starting policy calculations update...')
            )

            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('Running in dry-run mode - no changes will be saved')
                )
                # Wrap in transaction that we'll roll back
                with transaction.atomic():
                    updater.update_all_policy_calculations()
                    raise transaction.TransactionManagementError(
                        "Rolling back transaction - dry run mode"
                    )
            else:
                start_time = datetime.now()
                # Actually run and commit the updates
                updater.update_all_policy_calculations()
                end_time = datetime.now()
                elapsed_time = end_time - start_time
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully completed policy calculations update in {elapsed_time}'
                    )
                )
            self.stdout.write(
                self.style.SUCCESS('Successfully completed policy calculations update')
            )

        except Exception as e:
            logger.error(f"Error updating policy calculations: {str(e)}", exc_info=True)
            self.stderr.write(
                self.style.ERROR(f'Failed to update policy calculations: {str(e)}')
            )
            raise 
