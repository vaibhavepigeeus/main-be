from django.core.management.base import BaseCommand
from bankmanagement.models import CashAllocation, CashTrackerReport, PolicyType, LOB, BankTransaction, BankExchangeRate, BrokerInformation, PolicyInformation
from django.db.models import Q, DateField 
from django.db.models.functions import Cast
from decimal import Decimal
import logging
import pandas as pd  # Import pandas at the beginning of the file
from datetime import datetime, date
import calendar
from dateutil import parser
import csv

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Perform operations on CashAllocation and CashTrackerReport'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, help='Type of operation to perform: ca, lob, or create_ctr')
        parser.add_argument('--run', type=str, help='Flag to run the script for database chanegs')

    def handle(self, *args, **options):
        operation_type = options['type']
        run = options['run']

        if operation_type == 'ca':
            self.find_unassociated_cash_allocations()
        elif operation_type == 'create_ctr': #create cashtracker report
            self.create_ctr_for_unassociated_ca()
        elif operation_type == 'lob': #update lob and policy type
            self.update_lob_and_policy_type()
        elif operation_type == 'policy': #update policy from cashallocation
            self.update_policy_ctr()
        elif operation_type == 'coverholder': #update coverholder from policyinformation
            self.update_coverholder()
        elif operation_type == 'broker': #update broker name from brokerinformation
            self.update_broker_name()
        elif operation_type == 'pi': #update cashtracker from cashallocation
            self.update_policy_info(run)
        else:
            self.stdout.write(self.style.ERROR('Invalid operation type. Use --type ca, --type lob, or --type create_ctr'))

    def find_unassociated_cash_allocations(self):
        unassociated_cas = CashAllocation.objects.filter(archived=False)
        unassociated_cas_list = []
        for i in unassociated_cas:
            if not CashTrackerReport.objects.filter(cash_allocation=i).exists():
                unassociated_cas_list.append(i.id)
        logger.info(f'CashAllocation ID: {unassociated_cas_list} is unassociated')
        with open('unassociated_cas.txt', 'w') as f:
            for i in unassociated_cas_list:
                f.write(f'{i}\n')
        self.stdout.write(self.style.SUCCESS(f'Found {len(unassociated_cas_list)} unassociated CashAllocations:'))
    
    def get_accounting_date(date_of_month, is_date=True):
        year = date_of_month.year
        month = date_of_month.month
        last_day = calendar.monthrange(year, month)[1]

        last_day_of_month = date(year, month, last_day) if is_date else datetime(year, month, last_day)

        return last_day_of_month

    def get_accounting_date(self, date_of_month, is_date=True):
        """ This method to calculate accounting month year for current month """

        if not isinstance(date_of_month, (datetime, date)):
            logger.error(f"Invalid date passed: {date_of_month}")
            return None  # Or handle the error as appropriate for your application

        year = date_of_month.year
        month = date_of_month.month
        last_day = calendar.monthrange(year, month)[1]

        last_day_of_month = date(year, month, last_day) if is_date else datetime(year, month, last_day)

        return last_day_of_month

    def get_bank_exchange_rate(self, bank_transaction_obj):
        last_day_of_month = self.get_accounting_date(
            bank_transaction_obj.Payment_Receive_Date
        )
        logger.info(f"last_day_of_month: {last_day_of_month}")

        try:
            bank_exchange_rate_obj = BankExchangeRate.objects.get(
                currency_code=str(bank_transaction_obj.Bank_Currency_Code).strip(),
                month=last_day_of_month,
            )
            return bank_exchange_rate_obj.exchange_rate, last_day_of_month
        except BankExchangeRate.DoesNotExist:
            try:
                # If no exact match, get the latest record before the last_day_of_month
                bank_exchange_rate_obj = BankExchangeRate.objects.filter(
                    currency_code=str(bank_transaction_obj.Bank_Currency_Code).strip(),
                    month__lt=last_day_of_month,
                    month__isnull=False,
                ).latest("month")

                parsed_date = None
                if bank_exchange_rate_obj.month:
                    parsed_date = parser.parse(bank_exchange_rate_obj.month).date()

                return bank_exchange_rate_obj.exchange_rate, parsed_date
            except BankExchangeRate.DoesNotExist:
                raise ValueError(
                    "No valid exchange rate found for the given currency code."
                )
        
        
    def create_ctr_for_unassociated_ca(self):
        unassociated_cas = CashAllocation.objects.filter(id__in=self.get_unassociated_ca_ids(), archived=False)
        created_records = []  # Initialize a list to store data for the CSV

        for ca in unassociated_cas:
            bank_txn = ca.bank_txn
            bank_recon = bank_txn.bank_reconciliation if bank_txn and bank_txn.bank_reconciliation else None
            bank_roe, bank_roe_date = self.get_bank_exchange_rate(bank_txn)
            Receivable_Amount_calculated = round(Decimal(ca.receivable_amt) / bank_roe, 2)
            Allocated_Amount_calculated = round(Decimal(ca.allocated_amt) / bank_roe, 2)
            Remaining_Balance_calculated = round(Decimal(ca.unallocated_amt) / bank_roe, 2)
            # Create CashTrackerReport record
            ctr = CashTrackerReport(
                bank_txn=bank_txn,
                cash_allocation=ca,
                Accounting_Month=bank_txn.Accounting_Month if bank_txn else None,
                Bank_Charges=bank_recon.bank_charges if bank_recon else None,
                Receivable_Amount=ca.receivable_amt,
                Allocated_Amount=ca.allocated_amt,
                Remaining_Balance=ca.unallocated_amt,
                Receivable_Amount_calculated=Receivable_Amount_calculated,
                Allocated_Amount_calculated=Allocated_Amount_calculated,  
                Remaining_Balance_usd=Remaining_Balance_calculated,
                Invoice_Verification=ca.allocation_invoice_verification,
                Producing_Coverholder=ca.allocation_entity,
                Binding_Agreement=ca.binding_agreement,
                SCM_Partners=ca.allocation_scm,
                EEA_NonEEA=ca.allocation_eea,
                ROE_Bank_Statement=ca.bank_roe,
                Master_Binder=ca.allocation_binder,
                Policy=ca.policy_id,
                Cash_Reference=ca.cash_reference,
                GXB_Batch=ca.GXPbatchno,
                Allocation_Status=ca.allocation_status,
                System_Correction=ca.allocation_systemid,
                policy_information=ca.policy_fk if ca.policy_fk else None,
                Bank_Currency_Code=bank_txn.Bank_Currency_Code if bank_txn else None,
                Broker=bank_txn.Broker if bank_txn else None,
                Broker_Branch=bank_txn.Broker_Branch if bank_txn else None,
                Payment_Receive_Date=bank_txn.Payment_Receive_Date if bank_txn else None,
                Payment_Reference=bank_txn.Payment_Reference if bank_txn else None,
                Payment_Currency_Code=bank_txn.Bank_Currency_Code if bank_txn else None,
                PT_Receving_Bank_Account_Name=bank_txn.PT_Receving_Bank_Name if bank_txn else None,
                Receiving_Bank_Account=bank_txn.Receiving_Bank_Account if bank_txn else None,
                ROE=bank_roe,
                ROE_Date=bank_roe_date,
                created_by=ca.created_by,
                updated_by=ca.updated_by
            )
            ctr.save()
            logger.info(f'Created CashTrackerReport for CashAllocation ID: {ca.id}')

            # Append all data for this record to the list
            created_records.append({
                "CTR ID": ctr.id,
                "Cash Allocation ID": ca.id,
                "Bank Transaction ID": bank_txn.id if bank_txn else None,
                "Accounting Month": ca.accounting_monthyear,
                "Bank Charges": bank_recon.bank_charges if bank_recon else None,
                "Receivable Amount": ca.receivable_amt,
                "Allocated Amount": ca.allocated_amt,
                "Remaining Balance": ca.unallocated_amt,
                "Receivable Amount Calculated": Receivable_Amount_calculated,
                "Allocated Amount Calculated": Allocated_Amount_calculated,
                "Remaining Balance Calculated": Remaining_Balance_calculated,
                "Invoice Verification": ca.allocation_invoice_verification,
                "Producing Coverholder": ca.allocation_entity,
                "Binding Agreement": ca.binding_agreement,
                "SCM Partners": ca.allocation_scm,
                "EEA/Non-EEA": ca.allocation_eea,
                "ROE Bank Statement": ca.bank_roe,
                "Master Binder": ca.allocation_binder,
                "Policy": ca.policy_id,
                "Cash Reference": ca.cash_reference,
                "GXB Batch": ca.GXPbatchno,
                "Allocation Status": ca.allocation_status,
                "System Correction": ca.allocation_systemid,
                "Policy Information": ca.policy_fk.id if ca.policy_fk else None,
                "Bank_Currency_Code": bank_txn.Bank_Currency_Code if bank_txn else None,
                "Broker": bank_txn.Broker if bank_txn else None,
                "Broker Branch": bank_txn.Broker_Branch if bank_txn else None,
                "Payment Receive Date": bank_txn.Payment_Receive_Date if bank_txn else None,
                "Payment Reference": bank_txn.Payment_Reference if bank_txn else None,
                "Payment Currency Code": bank_txn.Bank_Currency_Code if bank_txn else None,
                "PT Receving Bank Account Name": bank_txn.PT_Receving_Bank_Name if bank_txn else None,
                "Receiving Bank Account": bank_txn.Receiving_Bank_Account if bank_txn else None,
                "Created By": ca.created_by,
                "Updated By": ca.updated_by
            })

        # Create a DataFrame and save it to CSV
        if created_records:
            df = pd.DataFrame(created_records)
            df.to_csv('complete_ctr_records.csv', index=False)
            self.stdout.write(self.style.SUCCESS(f'Created {len(created_records)} complete CashTrackerReports and saved to CSV'))

    def get_unassociated_ca_ids(self):
        with open('unassociated_cas.txt', 'r') as f:
            return [int(line.strip()) for line in f.readlines()]

    def update_lob_and_policy_type(self):
        cash_tracker_reports = CashTrackerReport.objects.filter(Policy__isnull=False)
        updated_count = 0
        data = []

        for ctr in cash_tracker_reports:
            print(ctr.id)
            policy_line_ref = ctr.Policy
            old_lob = ctr.LOB
            old_pt = ctr.Policy_Type
            
            if policy_line_ref and policy_line_ref not in ['nan', 'null', 'nat', '', None]:
                print(policy_line_ref)
                try:
                    policy_type = PolicyType.objects.filter(policy_start_letter=policy_line_ref[0]).first()
                    lob = LOB.objects.filter(lob_code=policy_line_ref[1:3]).first()

                    update_fields = []
                    new_pt = policy_type.policy_type if policy_type else None
                    new_lob = lob.lob if lob else None

                    if policy_type and ctr.Policy_Type != new_pt:
                        print(ctr.Policy_Type, new_pt)
                        ctr.Policy_Type = new_pt
                        update_fields.append('Policy_Type')
                    if lob and ctr.LOB != new_lob:
                        print(ctr.LOB, new_lob)
                        ctr.LOB = new_lob
                        update_fields.append('LOB')

                    if update_fields:
                        updated_count += 1
                        ctr.save(update_fields=update_fields)
                        logger.info(f'Updated CTR ID: {ctr.id}, Policy Type: {ctr.Policy_Type}, LOB: {ctr.LOB}')
                    
                        # Append the data for this record to the list
                        data.append({
                            "ID": ctr.id,
                            "Policy": policy_line_ref,
                            "old LOB": old_lob,
                            "new LOB": new_lob,
                            "old PT": old_pt,
                            "new PT": new_pt,
                            "policy_line_lob":policy_line_ref[1:3],
                            "update_error":'Updated successfully',
                            "updated_at_old":ctr.updated_at,
                            "updated_at_new":datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "updated":'Updated'
                        })
                    else:
                        # Append the data for this record to the list
                        data.append({
                            "ID": ctr.id,
                            "Policy": policy_line_ref,
                            "old LOB": old_lob,
                            "new LOB": new_lob,
                            "old PT": old_pt,
                            "new PT": new_pt,
                            "policy_line_lob":policy_line_ref[1:3],
                            "update_error":'Updated successfully',
                            "updated_at_old":ctr.updated_at,
                            "updated_at_new":datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "updated":'Not Updated'
                        })
                except Exception as e:
                    data.append({
                        "ID": ctr.id,
                        "Policy": '',
                        "old LOB": '',
                        "new LOB": '',
                        "old PT": '',
                        "new PT": '',
                        "policy_line_lob":'',
                        "update_error":str(e),
                        "updated_at_old":ctr.updated_at,
                        "updated_at_new":datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "updated":'Error'
                    })
                    logger.error(f'Error updating CTR ID: {ctr.id}. Error: {str(e)}')
            else:
                # Handle missing or invalid policy
                ctr.Policy_Type = 'Missing Policy Number'
                ctr.LOB = 'Missing Policy Number'
                ctr.Producing_Coverholder = 'Missing Policy Number'
                ctr.YOA = 'Missing Policy Number'
                ctr.Binding_Agreement = 'Missing Policy Number'
                
                ctr.save(update_fields=['Policy_Type', 'LOB', 'Producing_Coverholder','YOA','Binding_Agreement'])
                updated_count += 1
                logger.info(f'Updated CTR ID: {ctr.id} with missing policy information')
                data.append({
                    "ID": ctr.id,
                    "Policy": 'Missing Policy Number',
                    "old LOB": old_lob,
                    "new LOB": 'Missing Policy Number',
                    "old PT": old_pt,
                    "new PT": 'Missing Policy Number',
                    "policy_line_lob":'',
                    "update_error":'Updated Missing successfully',
                    "updated_at_old":ctr.updated_at,
                    "updated_at_new":datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "updated":'Updated'
                })

        # Create a DataFrame and save it to CSV
        df = pd.DataFrame(data)
        df.to_csv('updated_lob_policy.csv', index=False)
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} CashTrackerReports and saved to CSV'))

    def update_broker_name(self):
        updated_records = 0
        with open('broker_name_audit1.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID', 'Old Broker Value', 'New BrokerValue', 'Old Broker Branch', 'New Broker Branch', 'Old broker information', 'New broker information', 'updated_at_old','updated_at_new','updated'])
            # data = BankTransaction.objects.filter(Broker__in=['', '[]', 'Not Found', 'NULL', None])
            data = BankTransaction.objects.filter(broker_information__isnull=True, archived=False)
            for i, bt in enumerate(data):
                if bt.Broker_Branch and bt.Broker_Branch not in ['', None]:
                    broker_info = BrokerInformation.objects.filter(branch=bt.Broker_Branch).first()
                    print(broker_info)
                    old_value = bt.Broker
                    if broker_info:
                        if broker_info.broker_name != bt.Broker:
                            bt.Broker = broker_info.broker_name
                            self.stdout.write(self.style.SUCCESS(f'Broker name updated'))
                        old_broker_information = bt.broker_information
                        if bt.broker_information is None:
                            bt.broker_information = broker_info
                        bt.save(update_fields=['Broker', 'broker_information'])
                        updated_records += 1
                        writer.writerow([bt.id, old_value, bt.Broker, 'Not updated', 'Not updated', old_broker_information, bt.broker_information.id, bt.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Updated'])

                    else:
                        writer.writerow([bt.id, old_value, 'Not Found', 'Not Found', 'Not Found', 'Not Found', 'Not Found', bt.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Not Updated'])
                else:
                    if bt.broker_information:
                        old_broker_branch = bt.Broker_Branch
                        old_broker = bt.Broker
                        old_broker_information = bt.broker_information
                        if bt.Broker != bt.broker_information.broker_name:
                            bt.Broker = bt.broker_information.broker_name
                        
                        if bt.Broker_Branch != bt.broker_information.branch:
                            bt.Broker_Branch = bt.broker_information.branch
                        
                        bt.save(update_fields=['Broker', 'Broker_Branch','broker_information'])
                        updated_records += 1
                        writer.writerow([bt.id, old_broker, bt.Broker, old_broker_branch, bt.Broker_Branch, old_broker_information, bt.broker_information.id,bt.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Updated'])

        self.stdout.write(self.style.SUCCESS(f'Updated {updated_records} broker names'))

    def update_coverholder(self):
        records = CashTrackerReport.objects.filter(Producing_Coverholder__isnull=True)
        updated_count = 0
        with open('coverholder_audit.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ctr_id','Policy', 'Coverholder', 'Coverholder ID','updated_at_old','updated_at_new','updated'])
            for i in records:
                print(i.Producing_Coverholder, i.Policy)
                coverholder = PolicyInformation.objects.filter(Policy_Line_Ref=i.Policy).exclude(Producing_Entity='NA').first()
                if coverholder:
                    i.Producing_Coverholder = coverholder.Producing_Entity
                    writer.writerow([i.id, i.Policy, i.Producing_Coverholder, coverholder.id, i.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Updated'])
                    updated_count += 1

                    i.save(update_fields=['Producing_Coverholder'])
                    print(f'Coverholder updated for {i.Policy}')
                else:
                    i.Producing_Coverholder = 'Missing Policy Number' if not i.Policy else None
                    updated_count += 1
                    i.save(update_fields=['Producing_Coverholder'])
                    writer.writerow([i.id, i.Policy, i.Producing_Coverholder, 'Not Found', i.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Not Updated'])
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} coverholders'))

    def update_policy_ctr(self):
        records = CashTrackerReport.objects.filter(Policy__isnull=True)
        updated_count = 0
        with open('policy_ctr_audit.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ctr_id','Old Policy', 'New Policy', 'Cashlalloaction id','updated_at_old','updated_at_new','updated'])
            for i in records:
                if i.cash_allocation:
                    old_policy = i.Policy
                    new_policy = i.cash_allocation.policy_id
                    if new_policy not in ['','nan', 'null', 'nat', None]:
                        i.Policy = new_policy
                        i.save(update_fields=['Policy'])
                        writer.writerow([i.id, old_policy, i.cash_allocation.policy_id, i.cash_allocation.id, i.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Updated'])
                        updated_count += 1
                    else:
                        writer.writerow([i.id, old_policy, new_policy, 'Not Found', i.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Not Updated'])
                else:
                    writer.writerow([i.id, i.Policy, 'Not Found', 'Not Found', i.updated_at, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Not Updated'])
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} policies'))

    def update_policy_info(self, run=None):
        cash_allocations = CashAllocation.objects.filter(manual_entry=True, archived=False)
        updated_records = []
        updated_count = 0
        for ca in cash_allocations:
            policy_infos = PolicyInformation.objects.filter(Policy_Line_Ref=ca.policy_id)
            if policy_infos.count() > 1:
                # Assuming policy_fk_id corresponds to a PolicyInformation record
                policy_fk_record = policy_infos.filter(
                    id=ca.policy_fk_id
                ).first()
                if policy_fk_record:
                    # Select another record to copy data from
                    source_record = policy_infos.filter(UMR_Number__isnull=False).exclude(id=ca.policy_fk_id).first()
                    if source_record:
                        fields_to_update = [
                            'Syndicate_Binder',
                            'UMR_Number',
                            'MOP',
                            'Producing_Entity'
                        ]
                        update_fields = []
                        old_values = {}
                        new_values = {}
                        for field in fields_to_update:
                            old_value = getattr(policy_fk_record, field)
                            new_value = getattr(source_record, field)
                            if old_value in ['',None]:
                                setattr(policy_fk_record, field, new_value)
                                update_fields.append(field)
                                old_values[field] = old_value
                                new_values[field] = new_value

                        if update_fields:
                            updated_count += 1
                            if run.lower() == 'true':
                                policy_fk_record.save(update_fields=update_fields)
                                self.stdout.write(self.style.SUCCESS(f'Updated {len(update_fields)} fields for Policy FK ID: {policy_fk_record.id}'))
                            print(policy_fk_record.id)
                            updated_records.append({
                                'Policy FK ID': policy_fk_record.id,
                                'Updated Fields': update_fields,
                                'Old Values': old_values,
                                'New Values': new_values,
                                'Update Source': 'PolicyInformation'
                            })

        # Write audit information to CSV
        if updated_records:
            df = pd.DataFrame(updated_records)
            df.to_csv('policy_info_updates_audit.csv', index=False)
            self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} records in PolicyInformation and audit saved to CSV'))
    
    def revert_policy_info_updates(self):
        # Load the audit CSV file to get the records that were updated
        df = pd.read_csv('policy_info_updates_audit.csv')
        reverted_records = []

        for index, row in df.iterrows():
            policy_fk_id = row['Policy FK ID']
            updated_fields = eval(row['Updated Fields'])
            old_values = eval(row['Old Values'])

            # Fetch the policy information record
            policy_info = PolicyInformation.objects.filter(id=policy_fk_id).first()
            if policy_info:
                for field in updated_fields:
                    # Revert the changes by setting the old values
                    setattr(policy_info, field, old_values[field])

                # Save the reverted changes
                policy_info.save(update_fields=updated_fields)
                reverted_records.append({
                    'Policy FK ID': policy_fk_id,
                    'Reverted Fields': updated_fields,
                    'Reverted Values': old_values,
                    'Revert Source': 'PolicyInformation'
                })

        # Write revert audit information to CSV
        if reverted_records:
            df_reverted = pd.DataFrame(reverted_records)
            df_reverted.to_csv('policy_info_reverts_audit.csv', index=False)
            self.stdout.write(self.style.SUCCESS(f'Reverted {len(reverted_records)} records in PolicyInformation and revert audit saved to CSV'))