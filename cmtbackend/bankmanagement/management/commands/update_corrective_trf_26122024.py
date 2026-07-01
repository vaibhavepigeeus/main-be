"""
Script: update_bank_ac.py
Purpose: Django management command to update bank account details from an Excel file
Commands to run : python manage.py update_corrective_trf_26122024
Parameters:
1. --update true -> If wants to update records in database 
2. --update false -> If wants to generate only audit file 

This script reads bank account information from an Excel file, processes it against
the database, and outputs an updated Excel file with new bank account details and
any processing errors.
"""

from django.core.management.base import BaseCommand
import pandas as pd
from bankmanagement.models import BankDetails, CashAllocationCorrective
import os
from django.conf import settings

class Command(BaseCommand):
    """
    Django management command to update bank account details from an Excel file.
    
    This command processes an input Excel file containing bank account information,
    matches it with existing records in the database, and updates the same file
    with new bank account numbers and any processing errors.
    """
    
    help = 'Update bank account details directly in the input Excel file'

    def add_arguments(self, parser):
        # Adding new command line arguments
        parser.add_argument('--update', type=str, help='Flag for set update true of false')

    def handle(self, *args, **options):
        """
        Execute the command to process bank account updates.
        
        Args:
            *args: Variable length argument list.
            **options: Arbitrary keyword arguments.
            
        Returns:
            None. Updates the input Excel file with processed data.
            
        Side Effects:
            - Reads and updates 'CMT update required - Dec24.xlsx' in place
        """
        operation_type = options.get('update', 'false')  
        # Define input file path relative to Django project root
        excel_file = os.path.join(settings.BASE_DIR, "CMT update required - Dec24.xlsx")
        
        # Verify input file exists
        if not os.path.exists(excel_file):
            self.stdout.write(self.style.ERROR(f'Input file not found: {excel_file}'))
            return

        # Read the source Excel file containing bank details
        try:
            df = pd.read_excel(excel_file)
            self.stdout.write(self.style.SUCCESS(f'Successfully read file: {excel_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading Excel file: {str(e)}'))
            return

        # Initialize new columns for updated data and error tracking
        df['Cash Allocation Id'] = ''
        df['Cashallocation_corrective Table Id'] = ''
        df['Current Bank a/c #'] = ''
        df['Updated Bank a/c #'] = ''
        df['Exception'] = ''

        print('Operation type', operation_type)

        # Process each row in the Excel file
        for index, row in df.iterrows():
            if pd.isna(row['Corrective Trf ID']) or row['Corrective Trf ID'] == '':
                continue
            comment_row = row['Comments for Epigee Amendment 1']
            if 'Wrong PT bank account picked by CMT' not in comment_row:
                continue
            # Extract key fields for bank detail lookup
            entity = row['Producing Coverholder - Entity']
            currency = row['Bank Currency']

            # Query database for matching bank details
            bank_details = BankDetails.objects.filter(
                entity_number=entity,
                currency=currency
            )

            # Reset error for each row
            df.at[index, 'Exception'] = 'No matching bank details found'  # Default error

            # Case 1: Exactly one bank detail found - update information
            if pd.notna(row['Corrective Trf ID']) and row['Corrective Trf ID'] != '':
                df.at[index, 'Exception'] = ''  # Clear error if bank details found

                corrective = CashAllocationCorrective.objects.filter(
                    id=row['Corrective Trf ID']
                ).first()

                if corrective:
                    df.at[index, 'Cash Allocation Id'] = corrective.cash_allocation.id
                    df.at[index, 'Current Bank a/c #'] = corrective.PT_bank_acct_Number
                    df.at[index, 'Updated Bank a/c #'] = row['Corrected Bank A/C']
                    df.at[index, 'Cashallocation_corrective Id'] = corrective.id
                    if operation_type == 'true':
                        print(f'Updated account number for ID {corrective.id}: from {corrective.PT_bank_acct_Number} to {row["Corrected Bank A/C"]}')
                        corrective.PT_bank_acct_Number = row['Corrected Bank A/C']
                        corrective.save(update_fields=['PT_bank_acct_Number'])
                else:
                    df.at[index, 'Exception'] = 'Corrective transfer not found'

            # Case 2: Multiple bank details found - mark as error
            elif bank_details.count() > 1:
                df.at[index, 'Exception'] = f'Multiple bank details found : {list(bank_details.values_list("account_number", flat=True))}'
                # error_accounts = eval(row['Error'].split(': ')[1])  # Extract the list from the Exception message
                # matching_accounts = list(bank_details.values_list('account_number', flat=True))
                # if any(account in matching_accounts for account in error_accounts):
                #     corrective_trf_id = row['Corrective Trf ID']
                #     if pd.notna(corrective_trf_id) and corrective_trf_id != '':
                #         corrective = CashAllocationCorrective.objects.filter(id=corrective_trf_id).first()
                #         if corrective:
                #             df.at[index, 'Current Bank a/c #'] = corrective.bank_account
                #             df.at[index, 'Updated Bank a/c #'] = row['Corrected Bank A/C']  # Update with the first matching account
                #             df.at[index, 'Cashallocation_corrective Id'] = corrective.id
                #     else:
                #         df.at[index, 'Exception'] = 'Corrective transfer not found'

            # Case 3: No bank details found - error is already set to default

        # Save updates back to the same file
        try:
            df.to_excel(excel_file, index=False)
            self.stdout.write(self.style.SUCCESS(f'Successfully updated file: {excel_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error saving Excel file: {str(e)}'))
        self.stdout.write(self.style.SUCCESS('Successfully updated bank account details'))
