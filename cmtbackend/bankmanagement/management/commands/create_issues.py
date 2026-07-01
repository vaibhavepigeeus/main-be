'''
Class to create issues records for missing ids records
    -> python manage.py create_issues --dry-run

Note : --dry-run will only be passed if you want to replace data
'''

from django.core.management.base import BaseCommand
from bankmanagement.models import CashAllocationIssues, CashAllocation
from documents.models import CorrectionType
from django.utils import timezone
import csv
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Create CashAllocationIssues records based on cash_allocation_id'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in test mode without making database changes'
        )

    def handle(self, *args, **options):
        # Read cash_allocation_ids from ids.txt
        with open('ca_ids.txt', 'r') as file:
            cash_allocation_ids = [int(line.strip()) for line in file if line.strip().isdigit()]

        # Create audit directory if it doesn't exist
        audit_dir = 'audit_files'
        if not os.path.exists(audit_dir):
            os.makedirs(audit_dir)

        # Create audit file with timestamp and mode indicator
        mode = 'dry_run' if options['dry_run'] else 'actual'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audit_filename = f'{audit_dir}/cash_allocation_issues_audit_{mode}_{timestamp}.csv'
        
        # Define comprehensive audit CSV headers
        headers = [
            'execution_status',
            'error_message',
            'execution_timestamp',
            'mode',
            'cash_allocation_id',
            'issue_category',
            'issue_owner',
            'system_id',
            'comments',
            'assignment',
            'issue_date',
            'age_days',
            'isActive',
            'bank_txn_id',
            'policy_id',
            'policy_fk_id',
            'accounting_monthyear',
            'correction_type_desc',
            'correction_type',
            'correction_type_id'
        ]

        with open(audit_filename, 'w', newline='') as audit_file:
            writer = csv.DictWriter(audit_file, fieldnames=headers)
            writer.writeheader()

            for cash_allocation_id in cash_allocation_ids:
                try:
                    # Get the CashAllocation instance
                    cash_allocation = CashAllocation.objects.get(id=cash_allocation_id)
                    
                    # Get the CorrectionType instance
                    correction_type_instance = CorrectionType.objects.get(correction_type='Completed')
                    print(correction_type_instance)
                    # Prepare the data that would be created
                    issue_data = {
                        'issue_category': "Premium Payment",
                        'issue_owner': "nan",
                        'system_id': None,
                        'comments': "backend updated",
                        'assignment': "XFI",
                        'age_days': 0,
                        'isActive': True,
                        'bank_txn': cash_allocation.bank_txn,
                        'cash_allocation': cash_allocation,
                        'correction_type_desc': correction_type_instance.correction_description,
                        'correction_type': correction_type_instance
                    }

                    if options['dry_run']:
                        # In dry-run mode, just show what would be created
                        self.stdout.write("\nDRY RUN - The following record would be created:")
                        self.stdout.write("-" * 50)
                        for key, value in issue_data.items():
                            self.stdout.write(f"{key}: {value}")
                        self.stdout.write("-" * 50)
                        message = "Dry run completed - no database changes made"
                        created_issue_id = None
                    else:
                        # Actually create the record 
                        issue, created = CashAllocationIssues.objects.get_or_create(
                            cash_allocation_id=cash_allocation_id,
                            defaults=issue_data
                        )
                        if created:
                            message = f'Created issue record with ID: {issue.id}'
                        else:
                            message = f'Issue record already exists with ID: {issue.id}'
                        created_issue_id = issue.id

                    # Prepare audit data
                    audit_data = {
                        'execution_status': 'SUCCESS',
                        'error_message': message,
                        'execution_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'mode': mode,
                        'cash_allocation_id': cash_allocation.id,
                        'issue_category': "Premium Payment",
                        'issue_owner': "nan",
                        'system_id': None,
                        'comments': "system generated",
                        'assignment': "XFI",
                        'issue_date': None,
                        'age_days': 0,
                        'isActive': True,
                        'bank_txn_id': cash_allocation.bank_txn.id if cash_allocation.bank_txn else None,
                        'policy_id': None,
                        'policy_fk_id': None,
                        'accounting_monthyear': None,
                        'correction_type_desc': correction_type_instance.correction_description,
                        'correction_type': correction_type_instance.correction_type,
                        'correction_type_id': correction_type_instance.id
                    }

                    writer.writerow(audit_data)
                    self.stdout.write(self.style.SUCCESS(message))

                except CashAllocation.DoesNotExist:
                    error_msg = f'CashAllocation with ID {cash_allocation_id} does not exist'
                    writer.writerow({
                        'execution_status': 'ERROR',
                        'error_message': error_msg,
                        'execution_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'mode': mode,
                        'cash_allocation_id': cash_allocation_id,
                        **{field: None for field in headers[4:]}  # Fill remaining fields with None
                    })
                    self.stdout.write(self.style.ERROR(error_msg))

                except Exception as e:
                    error_msg = f'Error processing record: {str(e)}'
                    writer.writerow({
                        'execution_status': 'ERROR',
                        'error_message': error_msg,
                        'execution_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'mode': mode,
                        'cash_allocation_id': cash_allocation_id,
                        **{field: None for field in headers[4:]}  # Fill remaining fields with None
                    })
                    self.stdout.write(self.style.ERROR(error_msg))

        self.stdout.write(
            self.style.SUCCESS(f'Audit file created: {audit_filename}')
        )
