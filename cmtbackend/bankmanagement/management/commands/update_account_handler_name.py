'''
Class to update cash allocation and policy info details
    -> python manage.py update_account_handler_name --type 'Save'

Note : Type will only be passed if you want to replace data
'''

from django.core.management.base import BaseCommand
import pandas as pd
import logging

from bankmanagement.models import BankTransaction
from users.models import Users

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update Original Amount in Policy Information Table'

    def add_arguments(self, parser):
        # Adding new command line arguments
        parser.add_argument('--type', type=str, help='Type of operation to perform: create excel or create excel and save data')
    
    def handle(self, *args, **options):
        operation_type = options.get('type', 'normal')
        self.update_data(operation_type)
 
    def update_data(self, operation_type: str):
        print("Updating Policy and CashAllocation Data")
        update_user = Users.objects.get(user_name="Manikant Dhiman")
        # Path to the Excel file
        excel_file_path = 'account_handler_update_file.xlsx'  # Replace with your actual file path
        df = pd.read_excel(excel_file_path, sheet_name="Sheet1")

        # Initialize an empty list to store audit data
        audit_data = []

        # Loop through each row in the original DataFrame
        for index, row in df.iterrows():
            if row['Bank Transaction ID']:
                try:
                    obj = BankTransaction.objects.get(id=row['Bank Transaction ID'])
                    if row['Account Handler'] == obj.Assigned_User.user_name:
                        audit_data.append({
                            "bank id": obj.pk,
                            "bank transaction id": row['Bank Transaction Number'],
                            "file account handler": row['Account Handler'],
                            "db account handler": obj.Assigned_User.user_name,
                            "new account handler": "Manikant Dhiman",
                            "error": ""
                        })
                        if operation_type == 'Save':
                            obj.Assigned_User = update_user
                            obj.save()
                    else:
                        audit_data.append({
                            "bank id": obj.pk,
                            "bank transaction id": row['Bank Transaction Number'],
                            "file account handler": row['Account Handler'],
                            "db account handler": obj.Assigned_User.user_name,
                            "new account handler": "Manikant Dhiman",
                            "error": "File and DB user name did not matched"
                        })
                except Exception as e:
                    audit_data.append({
                        "bank id": row['Bank Transaction ID'],
                        "bank transaction id": row['Bank Transaction Number'],
                        "file account handler": row['Account Handler'],
                        "db account handler": '',
                        "new account handler": "Manikant Dhiman",
                        "error": e
                    })
        
        # Create the final DataFrame
        audit_data_df = pd.DataFrame(audit_data)

        # Write the DataFrame to an Excel file
        audit_data_df.to_excel("account_handler_update.xlsx", index=False)
        self.stdout.write(self.style.SUCCESS(f'Successfully exported account handler data to account_handler_update.xlsx'))