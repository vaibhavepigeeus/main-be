'''
Class to update original amount over policy info table
    -> python manage.py update_policy_info_original_amt --type 'save_details'

Note : Type will only be passed if you want to replace data
'''

from django.core.management.base import BaseCommand
import pandas as pd
import logging

from documents.models import PolicyInformation

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update Original Amount in Policy Information Table'

    def add_arguments(self, parser):
        # Adding new command line arguments
        parser.add_argument('--type', type=str, help='Type of operation to perform: create excel or create excel and save data')
    
    def handle(self, *args, **options):
        operation_type = options.get('type', 'normal')
        self.update_policy_data(operation_type)
 
    def update_policy_data(self, operation_type: str):
        # Path to the Excel file
        excel_file_path = 'Prod_Update_Policy_Information_Original_Amount.xlsx'  # Replace with your actual file path
        df = pd.read_excel(excel_file_path)
 
        # Initialize new columns in the DataFrame
        df['Database ID'] = None
        df['Database Policy Line Reference'] = None
        df['Database Installment Agency Amount (Settlement)'] = None
        df['Database Installment Agency Amount (Original)'] = None
        df['Database Updated Original Amount'] = None
        df['Error'] = None
 
        # Loop through each row in the DataFrame and update the database
        for index, row in df.iterrows():
            policy_id = row['id']
            policy_line_ref = row['Policy Line Ref']
            installment_agency_amount_in_sett = row['Installment Agency Amount (Sett)']
            installment_agency_amount_in_orig = row['Installment Agency Amount (Orig)']
 
            # Fetch policy details from the database
            policy_details = PolicyInformation.objects.filter(
                id=policy_id, 
                Policy_Line_Ref=policy_line_ref, 
                Installment_Agency_Amount_in_Sett=installment_agency_amount_in_sett
            ).first()
            
            print("policy_details--------------------->", policy_details)
 
            # Update DataFrame with fetched data
            if policy_details:
                existing_archived = policy_details.archived
                print("existing_archived--------------------->", existing_archived)
                existing_policy_id = policy_details.id
                existing_policy_line_ref = policy_details.Policy_Line_Ref
                existing_installment_agency_amount_in_sett = policy_details.Installment_Agency_Amount_in_Sett
                existing_installment_agency_amount_in_orig = policy_details.Installment_Agency_Amount_in_Orig
                
                print("existing_installment_agency_amount_in_orig--------------------->", existing_installment_agency_amount_in_orig)
                
                # Update the DataFrame with existing data
                df.at[index, 'Database ID'] = existing_policy_id
                df.at[index, 'Database Policy Line Reference'] = existing_policy_line_ref
                df.at[index, 'Database Installment Agency Amount (Settlement)'] = existing_installment_agency_amount_in_sett
                df.at[index, 'Database Installment Agency Amount (Original)'] = existing_installment_agency_amount_in_orig
                df.at[index, 'Database Updated Original Amount'] = installment_agency_amount_in_orig  # Assuming no change initially
                
                if operation_type == "save_details":
                    policy_details.Installment_Agency_Amount_in_Orig = installment_agency_amount_in_orig
                    policy_details.save(update_fields=['Installment_Agency_Amount_in_Orig'])
            
            else:
                df.at[index, 'Error'] = "Record not found"
 
        # Write the updated DataFrame back to the Excel file
        df.to_excel(excel_file_path, index=False)
        self.stdout.write(self.style.SUCCESS(f'Successfully updated policy information.'))
