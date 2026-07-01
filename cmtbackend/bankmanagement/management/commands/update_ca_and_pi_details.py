'''
Class to update cash allocation and policy info details
    -> python manage.py update_ca_and_pi_details --type 'save_details'

Note : Type will only be passed if you want to replace data
'''

from django.core.management.base import BaseCommand
import pandas as pd
import logging

from bankmanagement.models import CashAllocation
from documents.models import CurrencyDetails, PolicyInformation

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
        # Path to the Excel file
        excel_file_path = 'Rupesh misac nov 2024 - Values to be validated.xlsx'  # Replace with your actual file path
        df = pd.read_excel(excel_file_path, sheet_name="Instalment,settlement,org curr")

        # Convert NaN to None explicitly (if required)
        df = df.where(pd.notna(df), None)

        # Initialize an empty list to store audit data
        audit_data = []

        # variable to count the updated values
        count = 0

        # Loop through each row in the original DataFrame
        for index, row in df.iterrows():
            policy_id = row['Policy_fk_id']
            cash_allocation_id = row['Cash Allocation ID']
            try:
                installment = row['Installment #']
                installment_due_date = row['Installment Due Date.1']
                installment_amount = row['Installment Amount']
                settlement_currency = row['Settlement Currency']
                settlement_currency_id = None

                # Fetch policy details
                policy_details = PolicyInformation.objects.filter(id=policy_id).first()
                if policy_details:
                    policy_instalment = policy_details.Instalment_Nbr
                    policy_due_date = policy_details.Installment_Due_date
                    policy_amount = policy_details.Installment_Agency_Amount_in_Orig
                    policy_currency = policy_details.Settlement_Ccy
                else:
                    policy_instalment = policy_due_date = policy_amount = policy_currency = None

                # Fetch cash allocation details
                cash_allocation_details = CashAllocation.objects.filter(id=cash_allocation_id).first()
                if cash_allocation_details:
                    cash_installment = cash_allocation_details.installment_number
                    cash_due_date = cash_allocation_details.installment_duedate
                    cash_amount = cash_allocation_details.installment_amount_org
                    cash_currency = cash_allocation_details.settlement_currency
                    cash_currency_id = cash_allocation_details.settlement_ccy
                    cash_original_currency = cash_allocation_details.original_ccy
                else:
                    cash_installment = cash_due_date = cash_amount = cash_currency = cash_currency_id = cash_original_currency = None

                # Fetch settlement currency ID
                currency_details = None
                if settlement_currency:
                    currency_code = cash_currency if cash_currency else settlement_currency
                    currency_details = CurrencyDetails.objects.get(currency_code=currency_code)
                    if currency_details:
                        settlement_currency_id = currency_details.id
    
                if policy_details:
                    # Updating PI values
                    policy_details.Instalment_Nbr = installment
                    policy_details.Installment_Due_date = installment_due_date
                    policy_details.Installment_Amount_Syndicate_Share_in_Orig = cash_amount if cash_amount else installment_amount
                    policy_details.Settlement_Ccy = cash_currency if cash_currency else settlement_currency
                    policy_details.Original_Ccy = cash_original_currency
                else:
                    audit_row["Error"] = "Policy Details Missing"
                
                if cash_allocation_details:
                    # Updating Cash Allocation Values
                    cash_allocation_details.installment_number = installment
                    cash_allocation_details.installment_duedate = installment_due_date
                    cash_allocation_details.installment_amount_org = cash_amount if cash_amount else installment_amount
                    cash_allocation_details.settlement_currency = cash_currency if cash_currency else settlement_currency
                    cash_allocation_details.settlement_ccy = currency_details if currency_details else None
                else:
                    audit_row["Error"] = audit_row["Error"] + "Cash Allocation Details Missing"

                # Add all details to a row dictionary
                audit_row = {
                    "Policy ID": policy_id,
                    "Policy Installement": policy_instalment,
                    "Policy Installement Due Date": policy_due_date,
                    "Policy Installement Amount": policy_amount,
                    "Policy Settlement Currency": policy_currency,
                    "Cash Allocation ID": cash_allocation_id,
                    "Cash Allocation Installement": cash_installment,
                    "Cash Allocation Installement Due Date": cash_due_date,
                    "Cash Allocation Installement Amount": cash_amount,
                    "Cash Allocation Settlement Currency": cash_currency,
                    "Cash Allocation Settlement Currency ID": cash_currency_id,
                    "Updated Installement": installment,
                    "Updated Installement Due Date": installment_due_date,
                    "Updated Installement Amount": cash_amount if cash_amount else installment_amount,
                    "Updated Settlement Currency": cash_currency if cash_currency else settlement_currency,
                    "Updated Settlement Currency Id": settlement_currency_id,
                    "Updated Original Currency": cash_original_currency,
                    "Error": ""
                }

                # Save the changes to the database
                if operation_type == "save_details":
                    count = count + 1
                    print(f"Updating Value Count = {count}")

                    if policy_details:
                        policy_details.save()

                    if cash_allocation_details:
                        cash_allocation_details.save()

            except Exception as e:
                # Handle errors and log them in the "Error" column
                audit_row = {
                    "Policy ID": policy_id,
                    "Policy Installement": None,
                    "Policy Installement Due Date": None,
                    "Policy Installement Amount": None,
                    "Policy Settlement Currency": None,
                    "Cash Allocation ID": cash_allocation_id,
                    "Cash Allocation Installement": None,
                    "Cash Allocation Installement Due Date": None,
                    "Cash Allocation Installement Amount": None,
                    "Cash Allocation Settlement Currency": None,
                    "Cash Allocation Settlement Currency ID": None,
                    "Updated Installement": None,
                    "Updated Installement Due Date": None,
                    "Updated Installement Amount": None,
                    "Updated Settlement Currency Id": None,
                    "Updated Settlement Currency": None,
                    "Error": str(e)  # Set to None unless an exception occurs
                }

            # Append the audit_row to the audit_data list
            audit_data.append(audit_row)

        # Create the final DataFrame
        audit_data_df = pd.DataFrame(audit_data)

        # Write the DataFrame to an Excel file
        audit_data_df.to_excel("audit_data.xlsx", index=False)
        print("DataFrame has been successfully exported to audit_data.xlsx")
