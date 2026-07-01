
from dateutil import parser
from django.core.management.base import BaseCommand
from django.db.models import Q, F
from datetime import datetime, date
from django.db.models.functions import TruncDate
from bankmanagement.models import *
import calendar
from decimal import Decimal
import csv

class Command(BaseCommand):
    help = 'Update amounts calculation'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data correction process...'))

        with open('before_update1.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['CA ID', 'CTR ID', 'Currency', 'CA Receivable Amt', 'CTR Receivable Amt', 'CA Allocated Amt', 'CTR Allocated Amt', 'CA Unallocated Amt', 'CTR Remaining Balance'])

        with open('after_update1.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['CA ID', 'CTR ID', 'Currency', 'ROE', 'CA Receivable Amt', 'CTR Receivable Amt', 'CA Allocated Amt', 'CTR Allocated Amt', 'CA Unallocated Amt', 'CTR Remaining Balance'])
        
        # Update USD amounts where conditions are met 
        with open('ca_ids.txt', 'r') as file:
            receivable_amt_lst = file.readlines()

        allocated_amt_lst = [6407,11831,13087]
        unallocated_amt_lst = [11809,12489,12926,13051,13015,13029,13055,13059,13058]
        
        ctr_amount_data = CashTrackerReport.objects.filter(cash_allocation__in=receivable_amt_lst)
        
        updated_ids = []
        for obj in ctr_amount_data:
            ca = obj.cash_allocation
            bank_obj = obj.bank_txn
            with open('before_update1.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([ca.id, obj.id, bank_obj.Bank_Currency_Code, ca.receivable_amt, obj.Receivable_Amount_calculated, ca.allocated_amt, obj.Allocated_Amount_calculated, ca.unallocated_amt, obj.Remaining_Balance_usd])
            self.stdout.write(self.style.SUCCESS(f"Before Update: {ca.id}, {obj.id}, {bank_obj.Bank_Currency_Code}, {ca.receivable_amt}, {obj.Receivable_Amount_calculated}, {ca.allocated_amt}, {obj.Allocated_Amount_calculated}, {ca.unallocated_amt}, {obj.Remaining_Balance_usd}"))
            try:
                roe = self.get_bank_exchange_rate(bank_obj)
            except Exception as e:
                continue
            self.stdout.write(self.style.SUCCESS(f"roe : {roe}"))
            receivable_amt_usd = round(ca.receivable_amt / roe, 2)
            remaining_amt_usd = 0
            allocated_amt_usd = 0
            # remaining_amt_usd = round(ca.unallocated_amt / roe, 2)
            # allocated_amt_usd = round(ca.allocated_amt / roe, 2)
            # obj.Remaining_Balance_usd = remaining_bal_usd
            # obj.Allocated_Amount_calculated = allocated_amt_usd
            # obj.Receivable_Amount_calculated = receivable_amt_usd
            # obj.save()
            updated_ids.append(obj.id)
            with open('after_update1.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([ca.id, obj.id, bank_obj.Bank_Currency_Code, roe, ca.receivable_amt, receivable_amt_usd, ca.allocated_amt, allocated_amt_usd, ca.unallocated_amt, remaining_amt_usd])
            self.stdout.write(self.style.SUCCESS(f"After Update: {ca.id}, {obj.id}, {bank_obj.Bank_Currency_Code}, {roe}, {ca.receivable_amt}, {obj.Receivable_Amount_calculated}, {ca.allocated_amt}, {obj.Allocated_Amount_calculated}, {ca.unallocated_amt}, {obj.Remaining_Balance_usd}"))
        with open('updated_ids_ctr_amount.txt', 'w') as file:
            for record_id in updated_ids:
                file.write(f"{record_id}\n")

        self.stdout.write(self.style.SUCCESS('Data correction process completed successfully!'))

    def get_accounting_date(self, date_of_month, is_date=True):
        """ This method to calculate accounting month year for current month """

        year = date_of_month.year
        month = date_of_month.month
        last_day = calendar.monthrange(year, month)[1]

        last_day_of_month = date(year, month, last_day) if is_date else datetime(year, month, last_day)

        return last_day_of_month

    def get_bank_exchange_rate(self, bank_transaction_obj):
        today = datetime.now()
        last_day_of_month = self.get_accounting_date(today)

        try:
            bank_exchange_rate_obj = BankExchangeRate.objects.get(
                currency_code=str(bank_transaction_obj.Bank_Currency_Code).strip(),
                month=last_day_of_month,
            )
            return bank_exchange_rate_obj.exchange_rate
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
