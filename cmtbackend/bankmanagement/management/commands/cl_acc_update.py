import pandas as pd
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, now
from datetime import datetime
from bankmanagement.models import CashAllocation
from openpyxl import Workbook
from django.db.models import Q


class Command(BaseCommand):
    help = 'Updates the accounting_month field in the CashAllocation table and logs changes in an Excel file'


    def handle(self, *args, **options):
        target_date = make_aware(datetime(2024, 8, 31))
        with open('ca_ids.txt', 'r') as file:
            ca_ids = file.readlines()
            ca_ids = [int(id.strip()) for id in ca_ids]
        allocations = CashAllocation.objects.filter(id__in=ca_ids, archived=False)
        print(allocations.count())
        audit_trail = []

        for allocation in allocations:
            print(allocation.accounting_monthyear.month)
            print(allocation.accounting_monthyear.year)
            old_account_month = allocation.accounting_monthyear
            allocation.accounting_monthyear = target_date.date()

            allocation.save()
            audit_trail.append({
                "cash allocation id": allocation.id,
                "existing accounting month": old_account_month,
                "updated accounting month": target_date.date(),
                "allocation date": allocation.allocation_date,
                "update date": now()
            })
            print(f"{allocation.id}, {old_account_month}, {target_date}, {allocation.allocation_date}")

        print('selected records : ',len(audit_trail))
        # Create a DataFrame from the audit trail list
        df = pd.DataFrame(audit_trail)
        # Save the DataFrame to a CSV file
        df.to_csv('audit_trail_accounting_month_update.csv', index=False)


        self.stdout.write(self.style.SUCCESS('Successfully updated accounting months and created audit trail.'))