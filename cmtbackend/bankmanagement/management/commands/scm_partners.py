'''
Class to correct scm partner names

 -> python manage.py scm_partners --old_scm {old_scm_partner_name("Acrisure, LLC")} --new_scm {new_scm_partner_name("Acrisure LLC")}'
'''

from django.core.management.base import BaseCommand
from bankmanagement.models import CashTrackerReport
import pandas as pd
from datetime import datetime
import os

class Command(BaseCommand):
    help = 'Update SCM_Partner from "Acrisure, LLC" to "Acrisure LLC" and create audit log'

    def add_arguments(self, parser):
        # Adding new command line arguments
        parser.add_argument('--old_scm', type=str, help='Old scm name needs to be udpated')
        parser.add_argument('--new_scm', type=str, help='New scm name which will be updated')

    def handle(self, *args, **options):
        old_scm = options.get('old_scm', 'normal')  
        new_scm = options.get('new_scm', 'normal')

        try:
            # Get records before update and convert to DataFrame
            records_to_update = CashTrackerReport.objects.filter(
                SCM_Partners=old_scm
            ).values('id', 'SCM_Partner', 'updated_at')
            
            # Create DataFrame with current data
            df = pd.DataFrame(records_to_update)
            
            if not df.empty:
                # Add new columns for audit
                df['Old Name'] = df['SCM_Partner']
                df['New Name'] = new_scm
                df['Updated At Old'] = df['updated_at']
                df['Updated At New'] = datetime.now()
                
                # Reorder and rename columns
                df = df[[
                    'id', 
                    'Old Name',
                    'New Name', 
                    'Updated At Old',
                    'Updated At New'
                ]]
                
                # Create audit directory if it doesn't exist
                audit_dir = 'audit_logs'
                os.makedirs(audit_dir, exist_ok=True)

                # Save audit log
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filename = os.path.join(audit_dir, f'scm_partner_update_{timestamp}.csv')
                df.to_csv(csv_filename, index=False)

                # Perform the update
                updated_count = CashTrackerReport.objects.filter(
                    SCM_Partners=old_scm
                ).update(
                    SCM_Partners=new_scm,
                    updated_at=datetime.now()
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully updated {updated_count} records in CashTrackerReport. '
                        f'Audit log created at {csv_filename}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'No records found matching {old_scm}')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating records: {str(e)}')
            )