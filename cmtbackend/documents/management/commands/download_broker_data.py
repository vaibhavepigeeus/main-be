from django.core.management.base import BaseCommand
from django.core.management.base import BaseCommand
from openpyxl import Workbook
import os
from documents.models import BrokerInformation

class Command(BaseCommand):
    help = 'Download Broker data and save as Excel file'

    def handle(self, *args, **kwargs):
        # Create a workbook and sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Brokers"

        # Headers
        headers = ['ID',
                    'Broker Name',
                    'Broker',
                    'Branch',
                    'Duplicate Count',
                    'SOA Received From Broker',
                    'Name',
                    'Email',
                    'Secondary Email',
                    'Phone Number',
                    'Broker Branch Location',
                    'Created By',
                    'Added Date And Time',
                    'Updated By',
                    'Updated Date And Time',
                    'Updated Fields'
                ]
        ws.append(headers)

        def strip_timezone(dt):
            return dt.replace(tzinfo=None) if dt and hasattr(dt, 'tzinfo') else dt


        # Add broker data
        for broker in BrokerInformation.objects.all():
            ws.append([
                broker.id,
                broker.broker_name,
                broker.broker,
                broker.branch,
                broker.duplicate_count,
                broker.soa_received_from_broker,
                broker.name,
                broker.get_decrypted_email() if broker.email else '',
                broker.secondary_email,
                broker.get_decrypted_phone_number() if broker.phone_number else '',
                broker.broker_branch_location,
                broker.created_by,
                strip_timezone(broker.addedDateAndTime),
                broker.updated_by,
                strip_timezone(broker.updatedDateAndTime),
                broker.updated_fields,
            ])
        # Save the file
        wb.save('broker_data.xlsx')

        self.stdout.write(self.style.SUCCESS(f'Successfully exported broker data to broker_data.xlsx'))