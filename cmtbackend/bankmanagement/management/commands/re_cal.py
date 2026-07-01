from dateutil import parser
from django.core.management.base import BaseCommand
from django.db.models import F, Value, CharField
from django.db.models.functions import Coalesce
from bankmanagement.models import CashAllocation, BankTransaction, BankExchangeRate, CashTrackerReport
from documents.models import BankExchangeRate as DocBankExchangeRate
from users.models import UserAuditHistory
from django.db.models.fields import DateField
from django.db.models.functions import Cast
import calendar
from datetime import date, datetime
from dateutil.parser import parse
from decimal import Decimal
import csv
from django.db import connection

class Command(BaseCommand):
    help = 'Generate data audit report for Cash Allocation'

    def handle(self, *args, **options):
        # Fetch all cash allocations from the view
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM financial_data_bankview01")  # Replace 'your_view_name' with the actual view name
            columns = [col[0] for col in cursor.description]
            view_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Prepare CSV file
        filename = f"data_audit_report_{datetime.now().date()}.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'Cash Allocation Id', 'CTR Id', 'Bank Currency Code', 'Policy', 'Receivable', 'Allocated', 'Remaining balance',
                'Receivable (current USD)', 'Allocated (current USD)', 'Remaining balance (current USD)',
                'Payment Receive Date', 'Accounting month', 'Allocation status',
                'ROE Month/Year', 'ROE', 'Receivable (USD)', 'Allocated (USD)', 'Remaining balance (USD)',
                'Difference Receivable', 'Difference Allocated', 'Difference Remaining balance',
                'historical', 'Has 500 Error'
            ])
            writer.writeheader()

            for i, ca in enumerate(view_data, 1):
                try:
                    bank_txn_id = BankTransaction.objects.get(id=ca['Bank Transaction ID'], archived=False)
                    if ca['allocation status'] == 'Allocated':
                        # Get current ROE
                        current_roe, roe_date = self.get_bank_exchange_rate(bank_txn_id, accouting_month=ca['accounting_monthyear'])
                    else:
                        # Get historical ROE
                        current_roe, roe_date = self.get_bank_exchange_rate(bank_txn_id)

                    # Calculate current USD values
                    receivable_current_usd = Decimal(ca['Receivable Amount (USD)'])
                    allocated_current_usd = Decimal(ca['Allocated Amount (USD)'])
                    remaining_current_usd = Decimal(ca['Remaining Balance (USD)'])

                    # Calculate historical USD values
                    receivable_usd = round(Decimal(ca['Receivable Settlement Amount']) / current_roe, 2)
                    allocated_usd = round(Decimal(ca['Allocated Amount']) / current_roe, 2)
                    remaining_usd = round(Decimal(ca['Remaining Balance']) / current_roe, 2)

                    # Calculate differences
                    diff_receivable = round(receivable_current_usd - receivable_usd, 2)
                    diff_allocated = round(allocated_current_usd - allocated_usd, 2)
                    diff_remaining = round(remaining_current_usd - remaining_usd, 2)

                    # Check for 500 error
                    has_error = self.check_for_500_error(ca['Cash Allocation ID'])

                    try:
                        ctr_rec = CashTrackerReport.objects.get(cash_allocation_id=ca['Cash Allocation ID'])
                        ctr_id = ctr_rec.id
                    except Exception as e:
                        ctr_id = None
                        print(f'Error: {e}')

                    try:
                        cash_allocation = CashAllocation.objects.get(id=ca['Cash Allocation ID'])
                        historical = cash_allocation.historical
                    except Exception as e:
                        historical = None
                        print(f'Error: {e}')

                    writer.writerow({
                        'Cash Allocation Id': ca['Cash Allocation ID'],
                        'CTR Id': ctr_id,
                        'Bank Currency Code': ca['Bank Currency'],
                        'Policy': ca['Policy'],
                        'Receivable': ca['Receivable Settlement Amount'],
                        'Allocated': ca['Allocated Amount'],
                        'Remaining balance': ca['Remaining Balance'],
                        'Receivable (current USD)': receivable_current_usd,
                        'Allocated (current USD)': allocated_current_usd,
                        'Remaining balance (current USD)': remaining_current_usd,
                        'Payment Receive Date': ca['Payment_Receive_Date'],
                        'Accounting month': ca['accounting_monthyear'],
                        'Allocation status': ca['allocation status'],
                        'ROE Month/Year': roe_date,
                        'ROE': current_roe,
                        'Receivable (USD)': receivable_usd,
                        'Allocated (USD)': allocated_usd,
                        'Remaining balance (USD)': remaining_usd,
                        'Difference Receivable': diff_receivable,
                        'Difference Allocated': diff_allocated,
                        'Difference Remaining balance': diff_remaining,
                        'historical': historical, #CA
                        'Has 500 Error': has_error #USER AUDIT HISTORY
                    })
                    print(f'Saved record {i}/{len(view_data)}')
                except Exception as e:
                    print(f'Error: {e}')

        self.stdout.write(self.style.SUCCESS(f'Data audit report generated: {filename}'))

    def get_accounting_date(self, date_of_month, is_date=True):
        """ This method to calculate accounting month year for current month """
        if isinstance(date_of_month, str):
            date_of_month = parse(date_of_month)
        year = date_of_month.year
        month = date_of_month.month
        last_day = calendar.monthrange(year, month)[1]

        last_day_of_month = date(year, month, last_day) if is_date else datetime(year, month, last_day)

        return last_day_of_month

    def get_bank_exchange_rate(self, bank_transaction_obj, accouting_month=None):
        if accouting_month:
            last_day_of_month = self.get_accounting_date(accouting_month)
        else:
            last_day_of_month = self.get_accounting_date(
                bank_transaction_obj.Payment_Receive_Date
            )
        print(f"last_day_of_month: {last_day_of_month}")
        
        try:
            bank_exchange_rate_obj = BankExchangeRate.objects.get(
                currency_code=str(bank_transaction_obj.Bank_Currency_Code).strip(),
                month=last_day_of_month,
            )
            return bank_exchange_rate_obj.exchange_rate, last_day_of_month
        except BankExchangeRate.DoesNotExist:
            try:
                print(
                    f"BankExchangeRate.DoesNotExist: {bank_transaction_obj.Bank_Currency_Code} {last_day_of_month}"
                )
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

    def check_for_500_error(self, cash_allocation_id):
        return UserAuditHistory.objects.filter(
            api_url__contains=f'/api/bankmanagement/cash_allocation/{cash_allocation_id}/',
            response_status_code=500
        ).exists()