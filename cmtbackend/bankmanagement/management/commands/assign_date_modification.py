from django.core.management.base import BaseCommand
from bankmanagement.models import BankTransaction
from django.db.models import Q
import csv
from datetime import datetime

class Command(BaseCommand):
    help = 'Update assigned date for migrated data and generate audit trail'

    def handle(self, *args, **options):
        # Get all migrated bank transactions with null assigned date
        migrated_transactions = BankTransaction.objects.filter(
            Q(Uploaded_By='migrated') & Q(assigned_date__isnull=True),
            archived=False
        )

        audit_data = []

        for transaction in migrated_transactions:
            # Store audit information
            audit_entry = {
                'id': transaction.id,
                'bank_tx_id': transaction.Bank_Transaction_Id,
                'payment_received_date': transaction.Payment_Receive_Date,
                'assigned_date_before': transaction.assigned_date,
            }

            # Update assigned date to payment received date
            transaction.assigned_date = transaction.Payment_Receive_Date.date()
            transaction.save()

            # Complete audit entry
            audit_entry['assigned_date_after'] = transaction.assigned_date
            audit_entry['Uploaded_By'] = transaction.Uploaded_By
            audit_data.append(audit_entry)

        # Generate audit trail CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'assigned_date_update_audit_{timestamp}.csv'
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['id', 'bank_tx_id', 'payment_received_date', 'assigned_date_before', 'assigned_date_after', 'Uploaded_By']

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for entry in audit_data:
                writer.writerow(entry)

        self.stdout.write(self.style.SUCCESS(f'Successfully updated assigned dates and generated audit trail: {filename}'))
