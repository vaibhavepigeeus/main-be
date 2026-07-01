import pandas as pd
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, Max, Min, Count, F, Window
from django.db.models.functions import RowNumber
import os
import logging
import datetime
from decimal import Decimal
import time
from multiprocessing import Pool
import django
from django.db import connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmtbackend.settings')
django.setup()
logger = logging.getLogger('bankmanagement')
from .models import PolicyInformation, LOB, SiriusData, MOP_mapping, RBSDetails, BankExchangeRate, AON_Ledger, AgedDeptFileRecord


def parse_date(date_input):
    """Helper function to parse dates in multiple formats."""
    if not date_input:  # Handle None or empty string
        return None

    # If input is already a date object, return it
    if isinstance(date_input, datetime.date):
        return date_input

    # If input is a datetime object, extract the date
    if isinstance(date_input, datetime.datetime):
        return date_input.date()

    date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', '%Y/%m/%d', '%d/%m/%Y','%d-%b-%Y']

    for date_format in date_formats:
        try:
            return datetime.datetime.strptime(str(date_input), date_format).date()
        except ValueError:
            continue
    return None


class PolicyDatabaseUpdater:
    """Updates various fields in policy records using Pandas for optimization."""

    def __init__(self):
        self.logger = logger
        self.running_totals = {'cp_CT_Allcoated_Total_Agency': {}}

    def load_financial_data_bankview01(self):
        """
        Load financial_data_bankview01 data into a pandas DataFrame.
        This reduces the need for multiple SQL queries during policy calculations.
        """
        print("Loading financial_data_bankview01 data into DataFrame...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM financial_data_bankview01")
            columns = [col[0] for col in cursor.description]
            data = cursor.fetchall()

        # Create DataFrame from the query results
        bankview_df = pd.DataFrame(data, columns=columns)

        # Create aggregated views for common queries
        # 1. Sum of allocated amounts by policy
        allocated_by_policy = bankview_df.groupby("Policy")["Allocated Amount"].sum().reset_index()
        allocated_by_policy.columns = ["Policy", "total_allocated"]

        # 2. Sum of remaining balances by policy
        remaining_by_policy = bankview_df.groupby("Policy")["Remaining Balance"].sum().reset_index()
        remaining_by_policy.columns = ["Policy", "sum_amount"]

        # 3. Max allocation date by policy - using SQL directly to avoid pandas aggregation issues
        print("Getting max allocation dates using SQL...")
        max_allocation_date_dict = {}
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT "Policy", MAX("Allocation Date") as last_date
                FROM financial_data_bankview01
                GROUP BY "Policy"
            """)
            for row in cursor.fetchall():
                policy, last_date = row
                max_allocation_date_dict[policy] = last_date

        # Convert the dictionary to a DataFrame
        max_allocation_date = pd.DataFrame({
            "Policy": list(max_allocation_date_dict.keys()),
            "last_allocation_date": list(max_allocation_date_dict.values())
        })
        print(f"Found max allocation dates for {len(max_allocation_date)} policies")

        print(f"Loaded {len(bankview_df)} rows from financial_data_bankview01")
        return bankview_df, allocated_by_policy, remaining_by_policy, max_allocation_date

    def load_data_into_dataframe(self, file_name, SiriusPointsFile, MOPMappingFile, RBSDetailsFile, AONLedgerFile):
        """
        Load all relevant data into Pandas DataFrames.
        """
        # Load policies with annotations
        policies = PolicyInformation.objects.filter(file_name=file_name).annotate(
            gwp_sum=Sum('Gross_Written_Premium_Agency_Share_in_USD', filter=Q(archived=False)),
            received=Sum('Installment_Agency_Amount_in_Orig', filter=Q(archived=False)),
            nwp_sum=Sum('Net_Written_Premium_100_in_USD', filter=Q(archived=False)),
            installment_sum=Sum('Installment_Agency_Amount_in_USD'),
            lrgvers=Max('Policy_Version', filter=Q(archived=False))
        ).values()

        df = pd.DataFrame(policies)

        # Load related data
        sirius_data = SiriusData.objects.filter(file_name=SiriusPointsFile).values()
        mop_mapping = MOP_mapping.objects.filter(file_name=MOPMappingFile).values()
        rbs_details = RBSDetails.objects.filter(file_name=RBSDetailsFile).values()
        exchange_rates = BankExchangeRate.objects.all().values()
        aon_ledger = AON_Ledger.objects.filter(file_name=AONLedgerFile).values()
        lob_data = LOB.objects.all().values()

        # Load financial_data_bankview01 data
        bankview_df, allocated_by_policy, remaining_by_policy, max_allocation_date = self.load_financial_data_bankview01()

        # Convert related data to DataFrames
        sirius_df = pd.DataFrame(sirius_data)
        mop_df = pd.DataFrame(mop_mapping)
        rbs_df = pd.DataFrame(rbs_details)
        exchange_df = pd.DataFrame(exchange_rates)
        aon_df = pd.DataFrame(aon_ledger)
        lob_df = pd.DataFrame(lob_data)

        # Add missing columns with default values
        missing_columns = [
            'cashallocation', 'policy', 'cashallocationissues', 'policy_issues',
            'cashallocationcorrective', 'policy_corrective', 'cashallocationwriteoff',
            'policy_writeoff', 'cashallocationrefund', 'policy_refund', 'cashallocationcfi',
            'policy_cfi', 'crossallocation', 'policy_ca', 'cashallocationmsd', 'policy_msd',
            'premiumpayment', 'policy_premium', 'correctivetrf', 'policy_trf', 'cashtrackerreport'
        ]
        for col in missing_columns:
            if col not in df.columns:
                df[col] = None  # or 0, depending on the context

        return df, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, bankview_df, allocated_by_policy, remaining_by_policy, max_allocation_date

    def _get_last_allocation_date(self, policy_line_ref, max_allocation_date=None):
        """Helper method to get the last allocation date for a policy."""
        # If we have the pre-loaded DataFrame, use it
        if max_allocation_date is not None:
            # Find the row for this policy
            policy_row = max_allocation_date[max_allocation_date['Policy'] == policy_line_ref]
            if not policy_row.empty:
                return policy_row.iloc[0]['last_allocation_date']
            return ''

        print("fails to get from df so getting it from raw query...")
        # Fallback to SQL query if DataFrame is not available
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(MAX("Allocation Date"),'')
                FROM financial_data_bankview01
                WHERE "Policy" = %s
            """, [policy_line_ref])
            return cursor.fetchone()[0]

    # def get_running_total(self, column, policy_ref):
    #     """Helper function to get running total for a column and policy"""
    #     if column not in self.running_totals:
    #         self.running_totals[column] = {}
    #     if policy_ref not in self.running_totals[column]:
    #         self.running_totals[column][policy_ref] = 0
    #     return self.running_totals[column][policy_ref]

    def update_running_total(self, column, policy_ref, value):
        """Helper function to update running total for a column and policy"""
        if column not in self.running_totals:
            self.running_totals[column] = {}
        if policy_ref not in self.running_totals[column]:
            self.running_totals[column][policy_ref] = 0
        self.running_totals[column][policy_ref] += value

    def perform_calculations(self, df, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, file_name, AONLedgerFile, record_id, bankview_df=None, allocated_by_policy=None, remaining_by_policy=None, max_allocation_date=None, is_rerun=False):
        """
        Perform all calculations on the DataFrame.
        """
        record_obj = AgedDeptFileRecord.objects.get(pk=record_id)

        # Convert date columns to datetime.date
        date_columns = ['Expired_Date', 'Inception_Date', 'Date_Cancelled', 'Installment_Due_date']
        for col in date_columns:
            # Use .loc to avoid SettingWithCopyWarning
            df.loc[:, col] = pd.to_datetime(df[col], errors='coerce').dt.date
            df.loc[:, col] = df[col].apply(lambda x: x if pd.notnull(x) else None)

        # Add file_date column
        df.loc[:, 'file_date'] = datetime.datetime(2024, 9, 30).date()

        # Add reporting_date and window_end_date for Future Due calculations
        today = datetime.date.today()
        first_of_month = today.replace(day=1)
        df.loc[:, 'reporting_date'] = first_of_month - datetime.timedelta(days=1)
        df.loc[:, 'window_end_date'] = df['reporting_date'] + datetime.timedelta(days=45)

        # Prefetch BankExchangeRate data
        exchange_rates = BankExchangeRate.objects.all()
        exchange_rate_dict = {
            (rate.currency_code, rate.month): rate.exchange_rate for rate in exchange_rates
        }

        # First get policy versions
        policy_versions = {}
        print("Calculating policy versions...")
        # with connection.cursor() as cursor:
        #     cursor.execute(f"""
        #         SELECT id, ROW_NUMBER() OVER (PARTITION BY "Policy_Line_Ref" ORDER BY "created_at") AS version
        #         FROM documents_policyinformation
        #         WHERE file_name = '{file_name}'
        #     """)
        #     for row in cursor.fetchall():
        #         policy_id, version = row
        #         policy_versions[policy_id] = version

        policies_data = (
            PolicyInformation.objects
            .filter(file_name=file_name)
            .annotate(
                version=Window(
                    expression=RowNumber(),
                    partition_by=[F("Policy_Line_Ref")],
                    order_by=F("created_at").asc()
                )
            )
        )

        # Create the policy_versions dict
        policy_versions = {policy.id: policy.version for policy in policies_data}

        print(f"Found {len(policy_versions)} policy versions")

        # Fetch AON Ledger data separately
        aon_ledger_list = AON_Ledger.objects.filter(file_name=AONLedgerFile)

        # Create a dictionary for quick lookup of AON Ledger entries by insured key
        aon_ledger_dict = {
            ledger.assured[:8]: ledger for ledger in aon_ledger_list
        }

        # Get all policies that need updates
        print(f"Fetching policies requiring updates...{time.strftime('%H:%M:%S', time.localtime())}")
        policies = PolicyInformation.objects.filter(file_name=file_name).annotate(
            gwp_sum=Sum('Gross_Written_Premium_Agency_Share_in_USD', filter=Q(archived=False)),
            received=Sum('Installment_Agency_Amount_in_Orig', filter=Q(archived=False)),
            nwp_sum=Sum('Net_Written_Premium_100_in_USD', filter=Q(archived=False)),
            installment_sum=Sum('Installment_Agency_Amount_in_USD'),
            lrgvers=Max('Policy_Version', filter=Q(archived=False))
        )

        # Pre-fetch policy counts and payment status
        policy_counts = PolicyInformation.objects.filter(
            Policy_Line_Ref__in=policies.values_list('Policy_Line_Ref', flat=True)
        ).values('Policy_Line_Ref').annotate(count=Count('id'))

        print(f"policy fetching over...{time.strftime('%H:%M:%S', time.localtime())}")

        # Merge related data into the main DataFrame
        df = df.merge(sirius_df, how='left', left_on='Policy_Line_Ref', right_on='policy_line_reference', suffixes=('', '_sirius'))
        df = df.merge(mop_df, how='left', left_on='MOP', right_on='method_of_placement', suffixes=('', '_mop'))
        df = df.merge(rbs_df, how='left', left_on='Policy_Line_Ref', right_on='policy_line_reference', suffixes=('', '_rbs'))
        df = df.merge(lob_df, how='left', left_on='Policy_Line_Ref', right_on='lob_code', suffixes=('', '_lob'))

        # Update the process
        record_obj.progress = 20
        record_obj.save()

        self.logger.info("Starting field calculation0...")
        # Class of Business Update (BR)
        df['Class_of_Business_Remapped'] = df['Policy_Line_Ref'].str[1:3].map(lob_df.set_index('lob_code')['lob'])

        print(f"Starting field calculation1...{time.strftime('%H:%M:%S', time.localtime())}")
        # Facility Update (BS)
        df['Facility'] = df['UMR_Number'].str[-9:]

        print(f"Starting field calculation2...{time.strftime('%H:%M:%S', time.localtime())}")
        # SP_PER Update (BT)
        df['SP_PER'] = df['partner_percent_1'].apply(lambda x: f"{x}%" if pd.notnull(x) else "0.000%")

        print(f"Starting field calculation3...{time.strftime('%H:%M:%S', time.localtime())}")
        # MOP Mapped Update (BU)
        df['MOP_Mapped'] = df['MOP'].map(mop_df.set_index('method_of_placement')['mapped_mop'])

        print(f"Starting field calculation4...{time.strftime('%H:%M:%S', time.localtime())}")
        # Agency Commission Update (BV)
        df['Agency_Commission'] = df['mosaic_1609_agency_commission_pct'].apply(lambda x: f"{float(x) * 100:.3f}%" if pd.notnull(x) else 0)

        print(f"Starting field calculation5...{time.strftime('%H:%M:%S', time.localtime())}")
        # Brokerage Installment Settlement Update (BW)
        df['Brokerage_Installment_Sett'] = df.apply(
            lambda row: round(
                float(row['Installment_Agency_Amount_in_Sett'] or 0) *
                (float(row['Broker_Commision_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation6...{time.strftime('%H:%M:%S', time.localtime())}")
        # Gross_Written_Premium_100_USD_Agency_DUA_Earned (CD)
        df['Gross_Written_Premium_100_USD_Agency_DUA_Earned'] = df.apply(
            lambda row: round(
                row['gwp_sum'] if row['MOP_Mapped'] != "Facility/DUA"
                else (row['gwp_sum'] / (row['Expired_Date'] - row['Inception_Date']).days) *
                    (datetime.datetime(2024, 9, 30).date() - row['Inception_Date']).days,
                2
            ) if pd.notnull(row['gwp_sum']) and pd.notnull(row['Expired_Date']) and pd.notnull(row['Inception_Date'])
            else 0,
            axis=1
        )

        print(f"Starting field calculation7...{time.strftime('%H:%M:%S', time.localtime())}")
        df['Gross_Written_Premium_100_USD_Agency_DUA_Earned'] = df.apply(
            lambda row: round(
                row['gwp_sum'] if row['MOP_Mapped'] != "Facility/DUA"
                else (row['gwp_sum'] / max(1, (row['Expired_Date'] - row['Inception_Date']).days if pd.notnull(row['Expired_Date']) and pd.notnull(row['Inception_Date']) else 1)) *
                    ((row['file_date'] - row['Inception_Date']).days if pd.notnull(row['Inception_Date']) else 0),
                2
            ) if pd.notnull(row['gwp_sum']) and pd.notnull(row['Expired_Date']) and pd.notnull(row['Inception_Date'])
            else 0,
            axis=1
        )

        print(f"Starting field calculation8...{time.strftime('%H:%M:%S', time.localtime())}")
        # Agency Commission USD Update (BX)
        df['Agency_Commission_USD'] = df.apply(
            lambda row: round(
                float(row['Gross_Written_Premium_100_USD_Agency_DUA_Earned'] or 0) *
                (float(str(row['Agency_Commission']).rstrip('%') or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation9...{time.strftime('%H:%M:%S', time.localtime())}")
        # Sirius Point Amount Update (BY)
        df['Sirius_Point_Amount_GWP_USD'] = df.apply(
            lambda row: 0 if pd.isna(row['Broker_Commision_Pct']) or row['Broker_Commision_Pct'] == 0
            else round(
                (float(row['Installment_Agency_Amount_in_USD'] or 0) /
                (1 - float(row['Broker_Commision_Pct'] or 0) / 100)) * 0,
                2
            ),
            axis=1
        )

        print(f"Starting field calculation10...{time.strftime('%H:%M:%S', time.localtime())}")
        # Archre Amount GWP USD Update (BZ)
        df['Archre_Amount_GWP_USD'] = df.apply(
            lambda row: round(float(row['Sirius_Point_Amount_GWP_USD'] or 0) * 0.7, 2) if row['Class_of_Business_Remapped'] == "Professional Liability"
            else round(float(row['Sirius_Point_Amount_GWP_USD'] or 0), 2) if row['Class_of_Business_Remapped'] == "Cyber"
            else round(float(row['Sirius_Point_Amount_GWP_USD'] or 0) * 0.85, 2) if row['Class_of_Business_Remapped'] == "Political Risk"
            else 0,
            axis=1
        )

        print(f"Starting field calculation11...{time.strftime('%H:%M:%S', time.localtime())}")
        # Policy Version Update (DE)
        df.loc[:, 'Policy_Version'] = df['id'].map(policy_versions)

        print(f"Starting field calculation12...{time.strftime('%H:%M:%S', time.localtime())}")
        # First, ensure Installment_Agency_Amount_in_Orig is numeric
        df.loc[:, 'Installment_Agency_Amount_in_Orig'] = pd.to_numeric(df['Installment_Agency_Amount_in_Orig'], errors='coerce').fillna(0)

        # Then calculate instsum for each policy line reference
        print("Calculate instsum for each policy line reference1")
        try:
            # First check if the column is numeric
            print(f"Installment_Agency_Amount_in_Orig dtype: {df['Installment_Agency_Amount_in_Orig'].dtype}")

            # Apply cumsum operation
            df.loc[:, 'instsum'] = df.groupby('Policy_Line_Ref').apply(
                lambda x: x.sort_values('id')['Installment_Agency_Amount_in_Orig'].cumsum()
            ).reset_index(level=0, drop=True)

        except Exception as e:
            print(f"Error in first cumsum operation: {str(e)}")
            # Fallback: Try again with explicit conversion
            df.loc[:, 'Installment_Agency_Amount_in_Orig'] = pd.to_numeric(df['Installment_Agency_Amount_in_Orig'], errors='coerce').fillna(0)
            # Fix for SeriesGroupBy object has no attribute 'astype'
            # First convert to numeric, then group and apply cumsum
            df.loc[:, 'instsum'] = df.groupby('Policy_Line_Ref').apply(
                lambda x: pd.to_numeric(x.sort_values('id')['Installment_Agency_Amount_in_Orig'], errors='coerce').fillna(0).cumsum()
            ).reset_index(level=0, drop=True)

        print(f"Starting field calculation13...{time.strftime('%H:%M:%S', time.localtime())}")
        # cp_CT_Receivable_Total_Agency_Sett (CJ)
        df['cp_CT_Receivable_Total_Agency_Sett'] = df.apply(
            lambda row: round(
                Decimal('0') if pd.isna(row['received']) or float(row['received'] or 0) == 0
                else Decimal(str(row['received'] or 0)) - Decimal(str(row['instsum'] or 0)) if row['lrgvers'] == row['Policy_Version']
                else min(Decimal(str(row['received'] or 0)), Decimal(str(row['Installment_Agency_Amount_in_Sett'] or 0))) if float(row['received'] or 0) > float(row['Installment_Agency_Amount_in_Sett'] or 0)
                else Decimal(str(row['received'] or 0)) - Decimal(str(row['instsum'] or 0)),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation14...{time.strftime('%H:%M:%S', time.localtime())}")
        # CT Receivable Total Agency USD Gross Update (DK)
        df['cp_CT_Receivable_Total_Agency_USD_Gross'] = df.apply(
            lambda row: round(
                float(row['cp_CT_Receivable_Total_Agency_Sett'] or 0) if row['Settlement_Ccy'] == "USD"
                else float(row['cp_CT_Receivable_Total_Agency_Sett'] or 0) *
                    float(exchange_rate_dict.get((row['Settlement_Ccy'], 'latest'), 1)),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation15...{time.strftime('%H:%M:%S', time.localtime())}")
        # ArchRe Amount Received Update (CA)
        df['cp_ArchRe_Amount_Received'] = df.apply(
            lambda row: 0 if pd.isna(row['Sirius_Point_Amount_GWP_USD']) or float(row['Sirius_Point_Amount_GWP_USD'] or 0) == 0
            else round(
                float(row['cp_CT_Receivable_Total_Agency_USD_Gross'] or 0) *
                (float(str(row['SP_PER'] or '0').rstrip('%') or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation16...{time.strftime('%H:%M:%S', time.localtime())}")
        # ArchRe Outstanding Update (CB)
        df['cp_ArchRe_Outstanding'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Receivable_Total_Agency_USD_Gross']) or float(row['cp_CT_Receivable_Total_Agency_USD_Gross'] or 0) == 0
            else round(
                float(row['Archre_Amount_GWP_USD'] or 0) - float(row['cp_ArchRe_Amount_Received'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation17...{time.strftime('%H:%M:%S', time.localtime())}")
        # Commission Update (CC)
        df['Commission'] = df.apply(
            lambda row: 0 if pd.isna(row['Broker_Commision_Pct']) or float(row['Broker_Commision_Pct'] or 0) <= 0
            else round(
                float(row['Gross_Written_Premium_100_USD_Agency_DUA_Earned'] or 0) *
                (100 / float(row['Broker_Commision_Pct'] or 1)),  # Use 1 as fallback to prevent division by zero
                2
            ),
            axis=1
        )

        print(f"Starting field calculation18...{time.strftime('%H:%M:%S', time.localtime())}")
        # GWP 100 USD Syndicate Update (CE)
        df['Gross_Written_Premium_100_USD_Syndicate'] = df.apply(
            lambda row: round(
                float(row['Gross_Written_Premium_100_USD_Agency_DUA_Earned'] or 0) *
                (float(row['Signed_Order_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation19...{time.strftime('%H:%M:%S', time.localtime())}")
        # GWP 100 USD SCM Update (CF)
        df['Gross_Written_Premium_100_USD_SCM'] = df.apply(
            lambda row: round(
                float(row['Gross_Written_Premium_100_USD_Agency_DUA_Earned'] or 0) -
                float(row['Gross_Written_Premium_100_USD_Syndicate'] or 0),
                2
            ),
            axis=1
        )

        # Update the process
        record_obj.progress = 25
        record_obj.save()

        print(f"Starting field calculation20...{time.strftime('%H:%M:%S', time.localtime())}")
        # Net_Written_Premium_100_USD_Agency (CG)
        df['Net_Written_Premium_100_USD_Agency'] = df.apply(
            lambda row: 0 if pd.isna(row['Policy_Version']) or row['Policy_Version'] == 0 or row['MOP_Mapped'] not in ["Open Market", "Facility/DUA"]
            else round(
                float(row['nwp_sum'] or 0) * (float(row['Signed_Line_Pct'] or 0) / 100),
                2
            ) if row['MOP_Mapped'] == "Open Market" or (row['file_date'] - row['Inception_Date']).days > (row['Expired_Date'] - row['Inception_Date']).days
            else round(
                (float(row['nwp_sum'] or 0) * (float(row['Signed_Line_Pct'] or 0) / 100)) /
                max(1, (row['Expired_Date'] - row['Inception_Date']).days) *
                (row['file_date'] - row['Inception_Date']).days,
                2
            ),
            axis=1
        )

        print(f"Starting field calculation21...{time.strftime('%H:%M:%S', time.localtime())}")
        # Net Written Premium 100 USD Syndicate Update (CH)
        df['Net_Written_Premium_100_USD_Syndicate'] = df.apply(
            lambda row: round(
                float(row['Net_Written_Premium_100_USD_Agency'] or 0) *
                (float(row['Signed_Order_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation22...{time.strftime('%H:%M:%S', time.localtime())}")
        # Net Written Premium 100 USD SCM Update (CI)
        df['Net_Written_Premium_100_USD_SCM'] = df.apply(
            lambda row: round(
                float(row['Net_Written_Premium_100_USD_Agency'] or 0) -
                float(row['Net_Written_Premium_100_USD_Syndicate'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation23...{time.strftime('%H:%M:%S', time.localtime())}")
        # CT Receivable Total Syndicate Update (CK)
        df['cp_CT_Receivable_Total_Syndicate'] = df.apply(
            lambda row: round(
                float(row['cp_CT_Receivable_Total_Agency_Sett'] or 0) *
                (float(row['Signed_Order_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation24...{time.strftime('%H:%M:%S', time.localtime())}")
        # CT Receivable Total SCM Update (CL)
        df['cp_CT_Receivable_Total_SCM'] = df.apply(
            lambda row: round(
                float(row['cp_CT_Receivable_Total_Agency_Sett'] or 0) -
                float(row['cp_CT_Receivable_Total_Syndicate'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation25...{time.strftime('%H:%M:%S', time.localtime())}")
        # Get allocated amounts from bankview01 using the DataFrame if available
        print("Fetching allocated amounts...")
        if allocated_by_policy is not None:
            # Convert allocated_by_policy DataFrame to a dictionary for mapping
            allocated_data = dict(zip(allocated_by_policy['Policy'], allocated_by_policy['total_allocated']))
            print(f"Using pre-loaded DataFrame for allocated_data with {len(allocated_data)} policies")
        else:
            # Fallback to SQL query if DataFrame is not available
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT "Policy", COALESCE(SUM("Allocated Amount"), 0) AS allocated
                    FROM financial_data_bankview01
                    GROUP BY "Policy"
                """)
                allocated_data = {row[0]: row[1] for row in cursor.fetchall()}
                print(f"Using SQL query for allocated_data with {len(allocated_data)} policies")

        print(f"Starting field calculation26...{time.strftime('%H:%M:%S', time.localtime())}")
        # Add allocated amounts to DataFrame
        df.loc[:, 'allocated'] = df['Policy_Line_Ref'].map(allocated_data).fillna(0)

        print(f"Starting field calculation27...{time.strftime('%H:%M:%S', time.localtime())}")
        # Convert 'Installment_Agency_Amount_in_Orig' to numeric type
        df.loc[:, 'Installment_Agency_Amount_in_Orig'] = pd.to_numeric(df['Installment_Agency_Amount_in_Orig'], errors='coerce').fillna(0)

        print(f"Starting field calculation28...{time.strftime('%H:%M:%S', time.localtime())}")
        print("Calculate instsum for each policy line reference2")
        # Calculate instsum for each policy line reference
        try:
            # First check if the column is numeric
            print(f"Installment_Agency_Amount_in_Orig dtype (second cumsum): {df['Installment_Agency_Amount_in_Orig'].dtype}")

            # Apply cumsum operation
            df.loc[:, 'instsum'] = df.groupby('Policy_Line_Ref')['Installment_Agency_Amount_in_Orig'].cumsum()

        except Exception as e:
            print(f"Error in second cumsum operation: {str(e)}")
            # Fallback: Try again with explicit conversion
            df.loc[:, 'Installment_Agency_Amount_in_Orig'] = pd.to_numeric(df['Installment_Agency_Amount_in_Orig'], errors='coerce').fillna(0)
            # Fix for SeriesGroupBy object has no attribute 'astype'
            # First convert to numeric, then apply cumsum
            df.loc[:, 'instsum'] = df.groupby('Policy_Line_Ref')['Installment_Agency_Amount_in_Orig'].apply(lambda x: pd.to_numeric(x, errors='coerce').fillna(0).cumsum()).reset_index(level=0, drop=True)

        print(f"Starting field calculation29...{time.strftime('%H:%M:%S', time.localtime())}")
        # cp_CT_Allcoated_Total_Agency (CM) calculation
        df['cp_CT_Allcoated_Total_Agency'] = df.apply(
            lambda row: 0 if pd.isna(row['allocated']) or float(row['allocated'] or 0) == 0
            else round(
                float(row['allocated'] or 0) - float(row['instsum'] or 0),
                2
            ) if row['lrgvers'] == row['Policy_Version']
            else round(
                min(
                    float(row['Installment_Agency_Amount_in_Sett'] or 0),
                    float(row['allocated'] or 0) - float(row['instsum'] or 0)
                ),
                2
            ) if float(row['allocated'] or 0) - float(row['instsum'] or 0) > 0
            else 0,
            axis=1
        )

        # Update the process
        record_obj.progress = 30
        record_obj.save()

        # Update running total
        for index, row in df.iterrows():
            self.update_running_total('cp_CT_Allcoated_Total_Agency', row['Policy_Line_Ref'], row['cp_CT_Allcoated_Total_Agency'])

        print(f"Starting field calculation30...{time.strftime('%H:%M:%S', time.localtime())}")
        # cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt (CN)
        df['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'] = df.apply(
            lambda row: 0 if pd.isna(row['Expired_Date']) or pd.isna(row['Inception_Date']) or pd.isna(row['file_date'])
            else 0 if row['Date_Cancelled'] == row['Inception_Date']
            else round(
                ((row['Expired_Date'] - row['Inception_Date']).days / max(0.01, float(row['Installment_Agency_Amount_in_Sett'] or 0.01))) *
                (row['Date_Cancelled'] - row['Inception_Date']).days,
                2
            ) if row['Date_Cancelled'] and float(row['Net_Written_Premium_Agency_Share_in_Orig'] or 0) != 0
            else round(
                float(row['Installment_Agency_Amount_in_Sett'] or 0),
                2
            ) if row['MOP_Mapped'] != "Facility/DUA"
            else round(
                ((float(row['Installment_Agency_Amount_in_Sett'] or 0) / max(1, (row['Expired_Date'] - row['Inception_Date']).days)) *
                 (row['file_date'] - row['Inception_Date']).days) - float(row['cp_CT_Receivable_Total_Agency_Sett'] or 0),
                2
            ) if (row['file_date'] - row['Inception_Date']).days <= (row['Expired_Date'] - row['Inception_Date']).days
            else round(
                float(row['Installment_Agency_Amount_in_Sett'] or 0) - float(row['cp_CT_Receivable_Total_Agency_Sett'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation31...{time.strftime('%H:%M:%S', time.localtime())}")
        # Add range check for difference
        df['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'] = df.apply(
            lambda row: 0 if abs(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt']) <= abs(row['cp_CT_Unallocated'] or 0) + 50 and
                        abs(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt']) >= abs(row['cp_CT_Unallocated'] or 0) - 50
            else row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'],
            axis=1
        )

        print(f"Starting field calculation32...{time.strftime('%H:%M:%S', time.localtime())}")
        # cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD (CO)
        df['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt']) or pd.isna(row['Settlement_Ccy'])
            else round(
                float(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'] or 0) /
                float(exchange_rate_dict.get(
                    (row['Settlement_Ccy'], parse_date(row['Installment_Due_date'])),
                    exchange_rate_dict.get((row['Settlement_Ccy'], 'latest'), 1)
                )),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation33...{time.strftime('%H:%M:%S', time.localtime())}")
        # Money to Collect Syndicate Update (CP)
        df['cp_Money_To_Collect_Syndicate'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD']) or pd.isna(row['Signed_Order_Pct'])
            else round(
                float(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD'] or 0) *
                (float(row['Signed_Order_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation34...{time.strftime('%H:%M:%S', time.localtime())}")
        # Money to Collect USD SCM Update (CQ)
        df['cp_Money_To_Collect_USD_SCM'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD']) or pd.isna(row['cp_Money_To_Collect_Syndicate'])
            else round(
                float(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD'] or 0) -
                float(row['cp_Money_To_Collect_Syndicate'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation35...{time.strftime('%H:%M:%S', time.localtime())}")
        # Future Due 45 Days From Reporting Period Update (CR)
        df['Future_Due_45_Days_From_Reporting_Period'] = df.apply(
            lambda row: 0 if pd.isna(row['Installment_Due_date']) or pd.isna(row['Installment_Agency_Amount_in_USD'])
            else round(
                float(row['Installment_Agency_Amount_in_USD'] or 0)
                if row['Installment_Due_date'] and
                   row['reporting_date'] < row['Installment_Due_date'] <= row['window_end_date']
                else 0,
                2
            ),
            axis=1
        )

        print(f"Starting field calculation36...{time.strftime('%H:%M:%S', time.localtime())}")
        # CT Received vs Installment Syndicate Update (CS)
        df['cp_CT_Rcvd_vs_Instalment_Syndicate'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt']) or pd.isna(row['Signed_Order_Pct'])
            else round(
                float(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'] or 0) *
                (float(row['Signed_Order_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation37...{time.strftime('%H:%M:%S', time.localtime())}")
        # CT Received vs Installment SCM Update (CT)
        df['cp_CT_Rcvd_vs_Instalment_SCM'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt']) or pd.isna(row['cp_CT_Rcvd_vs_Instalment_Syndicate'])
            else round(
                float(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'] or 0) -
                float(row['cp_CT_Rcvd_vs_Instalment_Syndicate'] or 0),
                2
            ),
            axis=1
        )

        # Calculate duplicate_count for each policy line reference
        df.loc[:, 'duplicate_count'] = df.groupby('Policy_Line_Ref')['id'].transform('count')

        # Get sum_amount from bankview01 using the DataFrame if available
        print("Fetching sum_amount from bankview01...")
        if remaining_by_policy is not None:
            # Convert remaining_by_policy DataFrame to a dictionary for mapping
            sum_amount_data = dict(zip(remaining_by_policy['Policy'], remaining_by_policy['sum_amount']))
            print(f"Using pre-loaded DataFrame for sum_amount with {len(sum_amount_data)} policies")
        else:
            # Fallback to SQL query if DataFrame is not available
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT "Policy", COALESCE(SUM("Remaining Balance"), 0) AS sum_amount
                    FROM financial_data_bankview01
                    GROUP BY "Policy"
                """)
                sum_amount_data = {row[0]: row[1] for row in cursor.fetchall()}
                print(f"Using SQL query for sum_amount with {len(sum_amount_data)} policies")

        # Add sum_amount to DataFrame
        df.loc[:, 'sum_amount'] = df['Policy_Line_Ref'].map(sum_amount_data).fillna(0)

        print(f"Starting field calculation38...{time.strftime('%H:%M:%S', time.localtime())}")
        # cp_CT_Unallocated (CV)
        df['cp_CT_Unallocated'] = df.apply(
            lambda row: 0 if pd.isna(row['duplicate_count']) or row['duplicate_count'] > 1
            else round(
                float(row['sum_amount'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation39...{time.strftime('%H:%M:%S', time.localtime())}")
        # Unallocated USD Update (CW)
        df['cp_CT_Unallocated_USD'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Unallocated']) or pd.isna(row['Settlement_Ccy'])
            else round(
                float(row['cp_CT_Unallocated'] or 0) /
                float(exchange_rate_dict.get(
                    (row['Settlement_Ccy'], parse_date(row['Installment_Due_date'])),
                    exchange_rate_dict.get((row['Settlement_Ccy'], 'latest'), 1)
                )),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation40...{time.strftime('%H:%M:%S', time.localtime())}")
        # Unallocated USD Syndicate Update (CX)
        df['cp_CT_Unallocated_USD_Syndicate'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Unallocated_USD']) or pd.isna(row['Signed_Order_Pct'])
            else round(
                float(row['cp_CT_Unallocated_USD'] or 0) *
                (float(row['Signed_Order_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation41...{time.strftime('%H:%M:%S', time.localtime())}")
        # Unallocated USD SCM Update (CY)
        df['cp_CT_Unallocated_USD_SCM'] = df.apply(
            lambda row: 0 if pd.isna(row['cp_CT_Unallocated_USD']) or pd.isna(row['cp_CT_Unallocated_USD_Syndicate'])
            else round(
                float(row['cp_CT_Unallocated_USD'] or 0) -
                float(row['cp_CT_Unallocated_USD_Syndicate'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation42...{time.strftime('%H:%M:%S', time.localtime())}")
        # Brokerage USD Update (CZ)
        df['Brokerage_USD'] = df.apply(
            lambda row: 0 if pd.isna(row['Installment_Agency_Amount_in_USD']) or pd.isna(row['Broker_Commision_Pct'])
            else round(
                float(row['Installment_Agency_Amount_in_USD'] or 0) *
                (float(row['Broker_Commision_Pct'] or 0) / 100),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation43...{time.strftime('%H:%M:%S', time.localtime())}")
        # Agency Commission USD2 Update (DA)
        df['Agency_Commission_USD2'] = df.apply(
            lambda row: 0 if pd.isna(row['Installment_Agency_Amount_in_USD']) or pd.isna(row['Agency_Commission'])
            else round(
                float(row['Installment_Agency_Amount_in_USD'] or 0) *
                (float(str(row['Agency_Commission'] or '0').rstrip('%') or 0) / 100),
                2
            ),
            axis=1
        )

        # Update the process
        record_obj.progress = 35
        record_obj.save()

        print(f"Starting field calculation44...{time.strftime('%H:%M:%S', time.localtime())}")
        # cp_Aged_Bucket_By_Period_Receivable (DB)
        df['cp_Aged_Bucket_By_Period_Receivable'] = df.apply(
            lambda row: "Cancelled" if pd.notna(row['Policy_Status']) and row['Policy_Status'] == "Cancelled"
            else "Paid" if pd.notna(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt']) and -25 <= float(row['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'] or 0) <= 25
            else "Not Yet Due" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Open Market" and (
                pd.notna(row['Installment_Due_date']) and row['Installment_Due_date'] > row['file_date'] or
                pd.notna(row['Transaction_Status']) and row['Transaction_Status'] == "in interim" or
                pd.notna(row['Policy_Activity_Status']) and row['Policy_Activity_Status'] == "Firm Order Noted"
            )
            else "24+ Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Open Market" and pd.notna(row['file_date']) and pd.notna(row['Installment_Due_date']) and (row['file_date'] - row['Installment_Due_date']).days > 730
            else "12-24 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Open Market" and pd.notna(row['file_date']) and pd.notna(row['Installment_Due_date']) and (row['file_date'] - row['Installment_Due_date']).days > 365
            else "6-12 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Open Market" and pd.notna(row['file_date']) and pd.notna(row['Installment_Due_date']) and (row['file_date'] - row['Installment_Due_date']).days > 180
            else "3-6 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Open Market" and pd.notna(row['file_date']) and pd.notna(row['Installment_Due_date']) and (row['file_date'] - row['Installment_Due_date']).days > 90
            else "0-3 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Open Market"
            else "Not Yet Due" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Facility/DUA" and pd.notna(row['Expired_Date']) and row['Expired_Date'] + datetime.timedelta(days=90) > row['file_date']
            else "24+ Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Facility/DUA" and pd.notna(row['file_date']) and pd.notna(row['Expired_Date']) and (row['file_date'] - (row['Expired_Date'] + datetime.timedelta(days=90))).days > 730
            else "12-24 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Facility/DUA" and pd.notna(row['file_date']) and pd.notna(row['Expired_Date']) and (row['file_date'] - (row['Expired_Date'] + datetime.timedelta(days=90))).days > 365
            else "6-12 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Facility/DUA" and pd.notna(row['file_date']) and pd.notna(row['Expired_Date']) and (row['file_date'] - (row['Expired_Date'] + datetime.timedelta(days=90))).days > 180
            else "3-6 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Facility/DUA" and pd.notna(row['file_date']) and pd.notna(row['Expired_Date']) and (row['file_date'] - (row['Expired_Date'] + datetime.timedelta(days=90))).days > 90
            else "0-3 Months" if pd.notna(row['MOP_Mapped']) and row['MOP_Mapped'] == "Facility/DUA"
            else "Unknown Receivables" if pd.isna(row['MOP_Mapped']) and pd.notna(row['Installment_Due_date']) and row['Installment_Due_date'] < row['file_date']
            else "Not Yet Due",
            axis=1
        )

        print(f"Starting field calculation45...{time.strftime('%H:%M:%S', time.localtime())}")
        # AON_Collection_Status Update
        df['AON_Collection_Status'] = df.apply(
            lambda row: "Not AON" if pd.isna(row['Master_Broker']) or not str(row['Master_Broker']).lower().startswith("aon")
            else "Insured not found" if pd.isna(row['Insured'])
            else next(
                (ledger.status for ledger in aon_ledger_list
                 if pd.notna(row['Insured']) and str(row['Insured'])[:8] in ledger.assured
                 and pd.notna(row['Expired_Date']) and ledger.expiry_date == row['Expired_Date']),
                "Insured not found"
            ),
            axis=1
        )

        print(f"Starting field calculation46...{time.strftime('%H:%M:%S', time.localtime())}")
        # Last Allocation Date_CT Update (DF)
        df['Last_Allocation_Date_CT'] = df.apply(
            lambda row: None if pd.isna(row['Policy_Line_Ref'])
            else parse_date(
                self._get_last_allocation_date(row['Policy_Line_Ref'], max_allocation_date)
            ),
            axis=1
        )

        print(f"Starting field calculation47...{time.strftime('%H:%M:%S', time.localtime())}")
        # Sum of Installments vs NWP USD values 25 Update (DM)
        df['Sum_of_Inst_NWP_USD_values_25'] = df.apply(
            lambda row: None if (
                pd.isna(row['Policy_Version']) or
                row['Policy_Version'] != 0 or
                pd.notna(row['Policy_Status']) and row['Policy_Status'] == "Cancelled" or
                pd.isna(row['installment_sum']) or
                pd.isna(row['Net_Written_Premium_100_USD_Agency']) or
                abs(float(row['installment_sum'] or 0) - float(row['Net_Written_Premium_100_USD_Agency'] or 0)) <= 25
            )
            else round(
                float(row['installment_sum'] or 0) - float(row['Net_Written_Premium_100_USD_Agency'] or 0),
                2
            ),
            axis=1
        )

        print(f"Starting field calculation48...{time.strftime('%H:%M:%S', time.localtime())}")
        # Payment Received Check Update (DP)
        # Calculate the count of each Policy_Line_Ref in the DataFrame
        policy_line_ref_counts = df['Policy_Line_Ref'].value_counts().to_dict()

        # Create a dictionary to check if a Policy_Line_Ref has any records with "PAID" status
        policy_line_ref_paid_status = {}
        for policy_ref in policy_line_ref_counts.keys():
            # Check if any record with this Policy_Line_Ref has "PAID" status
            has_paid = df[(df['Policy_Line_Ref'] == policy_ref) &
                          (df['cp_Aged_Bucket_By_Period_Receivable'] == "Paid")].shape[0] > 0

            # Check if any record with this Policy_Line_Ref has cp_CT_Receivable_Total_Agency_Sett > 0
            has_positive_receivable = df[(df['Policy_Line_Ref'] == policy_ref) &
                                        (df['cp_CT_Receivable_Total_Agency_Sett'] > 0)].shape[0] > 0

            policy_line_ref_paid_status[policy_ref] = (has_paid or has_positive_receivable)

        # Implement the Excel formula using pandas apply
        df['Payment_Received'] = df.apply(
            lambda row: "Y" if (
                # First part of the OR condition in Excel formula
                (pd.notna(row['Policy_Line_Ref']) and
                 policy_line_ref_counts.get(row['Policy_Line_Ref'], 0) > 1 and
                 policy_line_ref_paid_status.get(row['Policy_Line_Ref'], False))
                # Second part of the OR condition in Excel formula
                or
                (pd.notna(row['Policy_Line_Ref']) and
                 policy_line_ref_counts.get(row['Policy_Line_Ref'], 0) == 1 and
                 (pd.notna(row['cp_Aged_Bucket_By_Period_Receivable']) and row['cp_Aged_Bucket_By_Period_Receivable'] == "Paid" or
                  pd.notna(row['cp_CT_Receivable_Total_Agency_Sett']) and float(row['cp_CT_Receivable_Total_Agency_Sett'] or 0) > 0))
            )
            else "N",
            axis=1
        )

        print(f"Starting field calculation49...{time.strftime('%H:%M:%S', time.localtime())}")
        # Original Currency vs Settlement Currency Check (DT)
        df['Original_Cur_vs_Settlement'] = df.apply(
            lambda row: False if (
                pd.isna(row['Settlement_Ccy']) or
                pd.isna(row['Original_Ccy']) or
                pd.isna(row['Installment_Agency_Amount_in_Orig']) or
                pd.isna(row['Installment_Agency_Amount_in_Sett'])
            )
            else (
                row['Settlement_Ccy'] == row['Original_Ccy'] and
                float(row['Installment_Agency_Amount_in_Orig'] or 0) == float(row['Installment_Agency_Amount_in_Sett'] or 0)
            ),
            axis=1
        )

        print(f"Starting field calculation50...{time.strftime('%H:%M:%S', time.localtime())}")
        # Currency Test Check (DU)
        df['Currency_Test'] = df.apply(
            lambda row: False if (
                pd.isna(row['Settlement_Ccy']) or
                pd.isna(row['Original_Ccy']) or
                pd.isna(row['Installment_Agency_Amount_in_Orig']) or
                pd.isna(row['Installment_Agency_Amount_in_Sett'])
            )
            else (
                (row['Settlement_Ccy'] == row['Original_Ccy'] and
                 float(row['Installment_Agency_Amount_in_Orig'] or 0) == float(row['Installment_Agency_Amount_in_Sett'] or 0)) or
                (row['Settlement_Ccy'] == row['Original_Ccy'] and
                 abs(float(row['Installment_Agency_Amount_in_Orig'] or 0) - float(row['Installment_Agency_Amount_in_Sett'] or 0)) < 25)
            ),
            axis=1
        )

        if not is_rerun:
            df['CT_Receivable_Total_Agency_USD_Gross'] = df['cp_CT_Receivable_Total_Agency_USD_Gross']
            df['ArchRe_Amount_Received'] = df['cp_ArchRe_Amount_Received']
            df['ArchRe_Outstanding'] = df['cp_ArchRe_Outstanding']
            df['CT_Receivable_Total_Syndicate'] = df['cp_CT_Receivable_Total_Syndicate']
            df['CT_Receivable_Total_Agency_Sett'] = df['cp_CT_Receivable_Total_Agency_Sett']
            df['CT_Receivable_Total_SCM'] = df['cp_CT_Receivable_Total_SCM']
            df['CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt'] = df['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt']
            df['CT_Unallocated'] = df['cp_CT_Unallocated']
            df['CT_Unallocated_USD'] = df['cp_CT_Unallocated_USD']
            df['CT_Unallocated_USD_Syndicate'] = df['cp_CT_Unallocated_USD_Syndicate']
            df['CT_Unallocated_USD_SCM'] = df['cp_CT_Unallocated_USD_SCM']
            df['Money_To_Collect_Syndicate'] = df['cp_Money_To_Collect_Syndicate']
            df['Money_To_Collect_USD_SCM'] = df['cp_Money_To_Collect_USD_SCM']
            df['CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD'] = df['cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD']
            df['CT_Rcvd_vs_Instalment_Syndicate'] = df['cp_CT_Rcvd_vs_Instalment_Syndicate']
            df['CT_Rcvd_vs_Instalment_SCM'] = df['cp_CT_Rcvd_vs_Instalment_SCM']
            df['Aged_Bucket_By_Period_Receivable'] = df['cp_Aged_Bucket_By_Period_Receivable']
            df['CT_Allcoated_Total_Agency'] = df['cp_CT_Allcoated_Total_Agency']

        # Update the process
        record_obj.progress = 40
        record_obj.save()

        return df

    def bulk_update_records(self, df, record_obj, chunk_size=500):
        """
        Convert the DataFrame back to Django model instances and perform a bulk update in chunks.
        Each chunk is processed within its own transaction, and if any chunk fails, all previous
        successful chunks are rolled back.

        Args:
            df: DataFrame containing policy records
            record_obj: AgedDeptFileRecord object for tracking progress
            chunk_size: Size of each chunk (default: 500)
        """
        if df is None or df.empty:
            self.logger.error("DataFrame is None or empty. No records to update.")
            return

        # Get the list of concrete fields in the PolicyInformation model
        concrete_fields = [field.name for field in PolicyInformation._meta.get_fields()
                          if field.concrete and not field.many_to_many and not field.primary_key]

        # Separate many-to-many fields
        m2m_fields = [field.name for field in PolicyInformation._meta.get_fields() if field.many_to_many]

        # Filter the DataFrame columns to include only the concrete fields
        df_filtered = df[concrete_fields + ['id']]

        # Convert DataFrame to a list of dictionaries
        records = df_filtered.to_dict('records')

        # Split records into chunks
        total_records = len(records)
        chunks = [records[i:i + chunk_size] for i in range(0, total_records, chunk_size)]
        num_chunks = len(chunks)
        self.logger.info(f"Split {total_records} records into {num_chunks} chunks of size {chunk_size}")
        self.logger.info(f"Starting bulk update at {time.strftime('%H:%M:%S', time.localtime())}")

        # Create a master savepoint that we can roll back to if any chunk fails
        sid = transaction.savepoint()

        try:
            # Process each chunk
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)} with {len(chunk)} records")

                # Convert dictionaries to model instances for this chunk
                updated_policies = []
                for record in chunk:
                    try:
                        # Create a new PolicyInformation instance with the 'id' for identification
                        policy = PolicyInformation(id=record['id'])
                        # Update the fields excluding 'id'
                        for field in concrete_fields:
                            if field in record and record[field] is not None:
                                setattr(policy, field, record[field])
                        updated_policies.append(policy)
                    except Exception as e:
                        self.logger.error(f"Error creating PolicyInformation instance: {str(e)}")
                        continue

                # Create a savepoint for this chunk
                chunk_sid = transaction.savepoint()

                try:
                    # Perform bulk update for this chunk
                    PolicyInformation.objects.bulk_update(updated_policies, concrete_fields)
                    # If successful, commit this chunk's savepoint
                    transaction.savepoint_commit(chunk_sid)
                    self.logger.info(f"Successfully updated chunk {i+1}/{len(chunks)}")

                    # Update progress
                    progress = 40 + int((i + 1) / len(chunks) * 35)  # Scale between 40-75%
                    record_obj.progress = min(progress, 75)
                    record_obj.save()
                    self.logger.info(f"Bulk update progress: {i+1}/{len(chunks)} chunks ({progress:.1f}%)")

                except Exception as e:
                    # If this chunk fails, roll back to the chunk's savepoint
                    transaction.savepoint_rollback(chunk_sid)
                    self.logger.error(f"Error during bulk update of chunk {i+1}: {str(e)}")
                    # Re-raise the exception to trigger the outer exception handler
                    raise Exception(f"Error during bulk update of chunk {i+1}: {str(e)}")

            # All chunks processed successfully
            record_obj.progress = 75
            record_obj.save()

            # Handle many-to-many fields separately
            self.logger.info(f"Starting many-to-many field updates for {len(chunks)} chunks")

            # Calculate total records for progress tracking
            total_m2m_records = sum(len(chunk) for chunk in chunks)
            processed_m2m_records = 0

            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing many-to-many fields for chunk {i+1}/{len(chunks)} with {len(chunk)} records")

                for record in chunk:
                    policy_id = record['id']
                    try:
                        policy = PolicyInformation.objects.get(id=policy_id)

                        for m2m_field in m2m_fields:
                            if m2m_field in df.columns:
                                try:
                                    # Get the many-to-many values from the DataFrame
                                    m2m_values = df.loc[df['id'] == policy_id, m2m_field].iloc[0]
                                    if m2m_values is not None:
                                        # Use .set() to update the many-to-many relationship
                                        getattr(policy, m2m_field).set(m2m_values)
                                        self.logger.debug(f"Updated many-to-many field {m2m_field} for policy {policy_id}")
                                except Exception as e:
                                    self.logger.error(f"Error updating many-to-many field {m2m_field} for policy {policy_id}: {str(e)}")
                    except Exception as e:
                        self.logger.error(f"Error retrieving policy with ID {policy_id}: {str(e)}")

                    # Update progress after each record
                    processed_m2m_records += 1
                    if processed_m2m_records % max(1, total_m2m_records // 20) == 0:  # Update ~20 times during process
                        progress = 75 + (processed_m2m_records / total_m2m_records * 25)  # Scale between 75-100%
                        record_obj.progress = min(progress, 99)  # Cap at 99% to leave room for final step
                        record_obj.save()
                        self.logger.info(f"M2M update progress: {processed_m2m_records}/{total_m2m_records} records ({progress:.1f}%)")

                # Update progress after each chunk
                progress = 75 + ((i + 1) / len(chunks) * 25)  # Scale between 75-100%
                record_obj.progress = min(progress, 99)  # Cap at 99% to leave room for final step
                record_obj.save()
                self.logger.info(f"Completed many-to-many updates for chunk {i+1}/{len(chunks)}")

            # If everything is successful, commit the master savepoint
            transaction.savepoint_commit(sid)

        except Exception as e:
            # If any chunk fails, roll back all changes to the master savepoint
            transaction.savepoint_rollback(sid)
            self.logger.error(f"Rolling back all updates due to error: {str(e)}")
            raise Exception(f"Error during chunked bulk update: {str(e)}")

    def parallel_processing(self, df, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, file_name, AONLedgerFile, record_id, bankview_df=None, allocated_by_policy=None, remaining_by_policy=None, max_allocation_date=None, chunk_size=1000):
        """
        Split the DataFrame into chunks and process them in parallel.
        """
        # Ensure numeric columns are properly converted before splitting into chunks
        numeric_columns = [
            'Installment_Agency_Amount_in_Orig',
            'Installment_Agency_Amount_in_Sett',
            'Installment_Agency_Amount_in_USD',
            'Gross_Written_Premium_Agency_Share_in_USD',
            'Net_Written_Premium_100_in_USD',
            'received',
            'gwp_sum',
            'nwp_sum',
            'installment_sum'
        ]

        for col in numeric_columns:
            if col in df.columns:
                df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Split the DataFrame into chunks
        chunks = [df[i:i + chunk_size] for i in range(0, df.shape[0], chunk_size)]

        # Update the process
        record = AgedDeptFileRecord.objects.get(pk=record_id)
        record.progress = 15
        record.save()

        # Check if we're in a daemon context
        import multiprocessing
        is_daemon = multiprocessing.current_process().daemon

        if is_daemon:
            # # We're in a daemon process, so we can't use multiprocessing.Pool
            # # Process chunks sequentially instead
            # self.logger.info("Running in daemon context - processing chunks sequentially")
            # processed_chunks = []
            # total_chunks = len(chunks)

            # for i, chunk in enumerate(chunks):
            #     # Update progress periodically
            #     if i % max(1, total_chunks // 10) == 0:  # Update progress ~10 times
            #         progress = 15 + int((i / total_chunks) * 75)  # Scale between 15-90%
            #         record.progress = min(progress, 89)  # Cap at 89% to leave room for final steps
            #         record.save()

            #     # Process the chunk
            #     result = self.perform_calculations(
            #         chunk, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df,
            #         file_name, AONLedgerFile, record_id,
            #         bankview_df=bankview_df, allocated_by_policy=allocated_by_policy,
            #         remaining_by_policy=remaining_by_policy, max_allocation_date=max_allocation_date
            #     )
            #     processed_chunks.append(result)
            self.logger.warning("Running inside a daemon process — skipping multiprocessing.")
            processed_chunks = [self.perform_calculations(
                chunk, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, file_name,
                AONLedgerFile, record_id, bankview_df, allocated_by_policy,
                remaining_by_policy, max_allocation_date
            ) for chunk in chunks]
        else:
            # Not in a daemon process, we can use multiprocessing
            self.logger.info("Processing chunks in parallel with multiprocessing")
            with Pool() as pool:
                processed_chunks = pool.starmap(self.perform_calculations, [
                    (chunk, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, file_name, AONLedgerFile, record_id,
                     bankview_df, allocated_by_policy, remaining_by_policy, max_allocation_date) for chunk in chunks
                ])

        # Concatenate the processed chunks
        result_df = pd.concat(processed_chunks)

        # Ensure numeric columns are properly converted after concatenation
        numeric_columns = [
            'Installment_Agency_Amount_in_Orig',
            'Installment_Agency_Amount_in_Sett',
            'Installment_Agency_Amount_in_USD',
            'Gross_Written_Premium_Agency_Share_in_USD',
            'Net_Written_Premium_100_in_USD',
            'received',
            'gwp_sum',
            'nwp_sum',
            'installment_sum',
            'instsum'
        ]

        for col in numeric_columns:
            if col in result_df.columns:
                result_df.loc[:, col] = pd.to_numeric(result_df[col], errors='coerce').fillna(0)

        return result_df

    def update_all_policy_calculations(self, file_name=None, record_id=None, AONLedgerFile=None, RBSDetailsFile=None, SiriusPointsFile=None, MOPMappingFile=None, chunk_size=500, is_rerun=False):
        """
        Combined function to handle all policy calculations in a single pass using Pandas.

        Args:
            file_name: Name of the policy file
            record_id: ID of the AgedDeptFileRecord
            AONLedgerFile: Name of the AON Ledger file
            RBSDetailsFile: Name of the RBS Details file
            SiriusPointsFile: Name of the Sirius Points file
            MOPMappingFile: Name of the MOP Mapping file
            chunk_size: Size of chunks for bulk update (default: 500)
            is_rerun: Boolean indicating if the calculation is a rerun
        """
        record = AgedDeptFileRecord.objects.get(pk=record_id)
        try:
            self.logger.info("Starting comprehensive policy calculations update...")
            start_time = time.time()

            # start the process updation
            record.progress = 1
            record.save()

            l_time = time.time()
            self.logger.info(f"Start load data...{l_time}")
            # Step 1: Load data into DataFrames
            df, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, bankview_df, allocated_by_policy, remaining_by_policy, max_allocation_date = self.load_data_into_dataframe(
                file_name, SiriusPointsFile, MOPMappingFile, RBSDetailsFile, AONLedgerFile
            )
            self.logger.info(f"Load data completed...{time.time() - l_time} seconds")

            # Update the process
            record.progress = 10
            record.save()

            p_time = time.time()
            self.logger.info(f"Perform calculations...{p_time}")
            # Step 2: Perform calculations in parallel
            # df = self.parallel_processing(df, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, file_name, AONLedgerFile, record_id,
            #                              bankview_df=bankview_df, allocated_by_policy=allocated_by_policy,
            #                              remaining_by_policy=remaining_by_policy, max_allocation_date=max_allocation_date)
            df = self.perform_calculations(df, sirius_df, mop_df, rbs_df, exchange_df, aon_df, lob_df, file_name, AONLedgerFile, record_id,
                                         bankview_df=bankview_df, allocated_by_policy=allocated_by_policy,
                                         remaining_by_policy=remaining_by_policy, max_allocation_date=max_allocation_date, is_rerun=is_rerun)
            self.logger.info(f"Calculation over...{time.time() - p_time} seconds")

            b_time = time.time()
            self.logger.info(f"Starting bulk update records in chunks of {chunk_size}...{time.strftime('%H:%M:%S', time.localtime())}")
            # Step 3: Bulk update records in chunks with transaction handling
            total_records = len(df)
            self.logger.info(f"Total records to update: {total_records}")
            self.bulk_update_records(df, record, chunk_size=chunk_size)
            update_time = time.time() - b_time
            self.logger.info(f"Chunked bulk update completed successfully in {update_time:.2f} seconds ({total_records/update_time:.2f} records/sec)...{time.strftime('%H:%M:%S', time.localtime())}")

            # Log completion
            elapsed_time = time.time() - start_time
            self.logger.info(f"Comprehensive policy calculations update completed in {elapsed_time:.2f} seconds")
            record.status = 'Success'
            record.progress = 100
            record.error_message = ""
            record.save()
            return "Policy calculations update completed successfully"

        except Exception as e:
            error_msg = f"Fatal error in policy calculations: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"record_id: {record_id}")
            self.logger.debug(f"record: {record}")
            record.status = 'Failed'  # Update status to 'Failed'
            record.error_message = error_msg
            record.save()
            return f"Comprehensive policy calculations update failed: {str(e)}"  # This is a return value, not an exception
