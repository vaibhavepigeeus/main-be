"""
Class to update amounts as per ROE

Updates BankTransaction and associated CashAllocation/CashTrackerReport amounts
based on Payment_Receive_Date in a single operation.

Usage:
    python manage.py bank_txn --cur_date '{date}'

Note: {date} is the last date of the prev-month
"""

import calendar
import csv
import logging
from datetime import date, datetime
from decimal import Decimal

import pandas as pd
from bankmanagement.models import (
    BankExchangeRate,
    BankTransaction,
    CashAllocation,
    CashTrackerReport,
)
from dateutil import parser
from dateutil.parser import parse
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Updates BankTransaction and associated CashAllocation amounts as per ROE based on Payment_Receive_Date"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cur_date",
            type=str,
            required=True,
            help="The Date after which transactions will be updated.",
        )

    def handle(self, *args, **options):
        cur_date = options.get("cur_date")

        if not cur_date:
            self.stdout.write(self.style.ERROR("Please provide --cur_date parameter"))
            return

        self.update_amounts_by_payment_date(cur_date)

    def update_cash_allocation_amounts(
        self, cash_allocation, bank_transaction, roe, roe_date
    ):
        """
        Update CashAllocation's associated CashTrackerReport amounts using the same ROE from BankTransaction.
        This ensures consistency - same ROE is used for both BankTransaction and its CashAllocations.
        """
        try:
            # Fetch related CashTrackerReport
            ctr_record = CashTrackerReport.objects.get(
                cash_allocation_id=cash_allocation.id
            )
        except CashTrackerReport.DoesNotExist:
            print(
                f"No CashTrackerReport found for CashAllocationID {cash_allocation.id}"
            )
            return None

        updated_rec = False
        updated_alc = False
        updated_rem = False

        old_receivable_amount = ctr_record.Receivable_Amount_calculated
        old_allocated_amount = ctr_record.Allocated_Amount_calculated
        old_remaining_balance = ctr_record.Remaining_Balance_usd

        new_receivable = round(Decimal(cash_allocation.receivable_amt) / roe, 2)
        ctr_record.Receivable_Amount_calculated = new_receivable

        new_allocated = round(Decimal(cash_allocation.allocated_amt) / roe, 2)
        ctr_record.Allocated_Amount_calculated = new_allocated

        new_remaining = round(Decimal(cash_allocation.unallocated_amt) / roe, 2)
        ctr_record.Remaining_Balance_usd = new_remaining

        ctr_record.ROE = roe
        ctr_record.ROE_Date = roe_date
        ctr_record.save(
            update_fields=[
                "Receivable_Amount_calculated",
                "Allocated_Amount_calculated",
                "Remaining_Balance_usd",
                "ROE",
                "ROE_Date",
            ]
        )

        return {
            "Cash_Allocation_ID": cash_allocation.id,
            "Bank_Txn_ID": bank_transaction.id,
            "Cash_Tracker_Report_ID": ctr_record.id,
            "Accounting_Month": cash_allocation.accounting_monthyear,
            "Policy_ID": cash_allocation.policy_id,
            "Bank_Currency_Code": bank_transaction.Bank_Currency_Code,
            "Payment_Receive_Date_BT": bank_transaction.Payment_Receive_Date,
            "ROE": roe,
            "ROE_Date": roe_date,
            "Receivable_Amt_CA": cash_allocation.receivable_amt,
            "Old_Receivable_Amount": old_receivable_amount,
            "New_Receivable_Amount_Calculated": ctr_record.Receivable_Amount_calculated,
            "Allocated_Amt_CA": cash_allocation.allocated_amt,
            "Old_Allocated_Amount": old_allocated_amount,
            "New_Allocated_Amount_Calculated": ctr_record.Allocated_Amount_calculated,
            "Unallocated_Amt_CA": cash_allocation.unallocated_amt,
            "Old_Remaining_Balance": old_remaining_balance,
            "New_Remaining_Balance_USD": ctr_record.Remaining_Balance_usd,
            "Updated_At_Old": ctr_record.updated_at,
            "Updated_At_New": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Updated_Rec": "Y" if updated_rec else "N/A",
            "Updated_Alc": "Y" if updated_alc else "N/A",
            "Updated_Rem": "Y" if updated_rem else "N/A",
        }

    def update_amounts_by_payment_date(self, cur_date: str):
        """
        Updates BankTransaction and associated CashAllocation/CashTrackerReport amounts
        based on Payment_Receive_Date. Creates audit CSV files.
        """
        transactions = BankTransaction.objects.filter(Payment_Receive_Date__gt=cur_date)
        print(f"Total BankTransactions to process: {len(transactions)}")

        bank_txn_data = []
        cash_allocation_data = []
        error_data = []
        bt_updated_count = 0
        ca_updated_count = 0

        for transaction in transactions:
            if not transaction.Payment_Receive_Date:
                continue

            # Fetch ROE
            try:
                roe, roe_date = self.get_bank_exchange_rate(transaction)
            except Exception as e:
                error_data.append(
                    {
                        "Bank_Txn_ID": transaction.id,
                        "Error": str(e),
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
                continue

            # Capture old values before update
            old_roe = transaction.ROE
            old_roe_date = transaction.ROE_Date
            old_receivable_amount_usd = transaction.Receivable_Amount_USD

            # Update BankTransaction amounts
            if self.update_bank_txn_amounts(transaction, roe, roe_date):
                bt_updated_count += 1
                bank_txn_data.append(
                    {
                        "Bank_Txn_ID": transaction.id,
                        "Receivable_Amount": Decimal(transaction.Receivable_Amount),
                        "Old_Receivable_Amount_USD": old_receivable_amount_usd,
                        "New_Receivable_Amount_USD": transaction.Receivable_Amount_USD,
                        "Bank_Currency_Code": transaction.Bank_Currency_Code,
                        "Old_ROE": old_roe,
                        "New_ROE": transaction.ROE,
                        "Old_ROE_Date": old_roe_date,
                        "New_ROE_Date": transaction.ROE_Date,
                        "Payment_Receive_Date": transaction.Payment_Receive_Date.date(),
                        "Accounting_Month": transaction.Accounting_Month,
                        "Date_Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            # Update associated CashAllocations (not filtering archived to handle edge cases)
            ca_for_txn = 0
            for ca in CashAllocation.objects.filter(bank_txn=transaction):
                ca_result = self.update_cash_allocation_amounts(
                    ca, transaction, roe, roe_date
                )
                if ca_result:
                    ca_updated_count += 1
                    ca_for_txn += 1
                    cash_allocation_data.append(ca_result)

            print(f"BankTxn {transaction.id} | CA updated: {ca_for_txn}")

        # Write audit CSV files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if bank_txn_data:
            pd.DataFrame(bank_txn_data).to_csv(
                f"bank_txn_audit_{cur_date}_{timestamp}.csv", index=False
            )
            print(
                f"Bank Transaction audit file: bank_txn_audit_{cur_date}_{timestamp}.csv"
            )

        if cash_allocation_data:
            pd.DataFrame(cash_allocation_data).to_csv(
                f"cash_allocation_audit_{cur_date}_{timestamp}.csv", index=False
            )
            print(
                f"Cash Allocation audit file: cash_allocation_audit_{cur_date}_{timestamp}.csv"
            )

        if error_data:
            pd.DataFrame(error_data).to_csv(
                f"error_audit_{cur_date}_{timestamp}.csv", index=False
            )
            print(f"Error audit file: error_audit_{cur_date}_{timestamp}.csv")

        # Summary
        print(
            f"\n=== SUMMARY: BankTxn={bt_updated_count}, CashAllocations={ca_updated_count}, Errors={len(error_data)} ==="
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {bt_updated_count} BankTransactions and {ca_updated_count} CashAllocations."
            )
        )

    def update_bank_txn_amounts(self, transaction, roe, roe_date):
        """Update USD Amount for BankTransaction based on ROE. Returns True if updated."""
        receivable_amount_usd = round(Decimal(transaction.Receivable_Amount) / roe, 2)

        # Only save if values have changed
        if (
            transaction.Receivable_Amount_USD != receivable_amount_usd
            or transaction.ROE != roe
            or transaction.ROE_Date != roe_date
        ):
            transaction.Receivable_Amount_USD = receivable_amount_usd
            transaction.ROE = roe
            transaction.ROE_Date = roe_date
            transaction.save(update_fields=["Receivable_Amount_USD", "ROE", "ROE_Date"])
            return True

        return False

    def get_accounting_date(self, date_of_month, is_date=True):
        """This method to calculate accounting month year for current month"""

        year = date_of_month.year
        month = date_of_month.month
        last_day = calendar.monthrange(year, month)[1]

        last_day_of_month = (
            date(year, month, last_day) if is_date else datetime(year, month, last_day)
        )

        return last_day_of_month

    def get_bank_exchange_rate(self, bank_transaction_obj):
        """
        Get exchange rate for the payment receive date month.
        Returns latest available rate <= target month.
        """
        last_day_of_month = self.get_accounting_date(
            bank_transaction_obj.Payment_Receive_Date
        )
        currency_code = str(bank_transaction_obj.Bank_Currency_Code).strip()

        try:
            bank_exchange_rate_obj = BankExchangeRate.objects.filter(
                currency_code=currency_code, month__lte=last_day_of_month
            ).latest("month")

            roe_date = parser.parse(bank_exchange_rate_obj.month).date()
            return bank_exchange_rate_obj.exchange_rate, roe_date
        except BankExchangeRate.DoesNotExist:
            raise ValueError(f"No exchange rate found for currency {currency_code}")
