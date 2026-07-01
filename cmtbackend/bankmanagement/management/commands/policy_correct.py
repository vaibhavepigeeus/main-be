from django.core.management.base import BaseCommand
from documents.models import PolicyInformation
from bankmanagement.models import CashAllocation, CashTrackerReport
import pandas as pd
from datetime import datetime
from django.db.models.functions import Length
from django.db.models import Q

class Command(BaseCommand):
    help = 'Find policy records and related cash allocations/trackers and export to CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['collect_plc', 'update_plc'],
            required=True,
            help='Operation type: collect_plc (collect data) or update_plc (update records)'
        )

    def handle(self, *args, **options):
        operation_type = options['type']
        
        if operation_type == 'collect_plc':
            self.collect_data()
        elif operation_type == 'update_plc':
            self.update_records()

    def collect_data(self):
        # Start with PolicyInformation records with length filter
        policies = PolicyInformation.objects.annotate(
            ref_length=Length('Policy_Line_Ref')
        ).filter(
            Q(ref_length=13) | Q(ref_length=26) | Q(ref_length=11),
            ~Q(Policy_Line_Ref=''),
            ~Q(Policy_Line_Ref='nan')
        ).values(
            'id',
            'Policy_Line_Ref',
            'ref_length'
        )

        # Convert to DataFrame
        df_policies = pd.DataFrame(list(policies))
        if not df_policies.empty:
            df_policies.columns = ['pi_id', 'Policy_Line_Ref[PI]', 'length[PI]']
        else:
            df_policies = pd.DataFrame(columns=['pi_id', 'Policy_Line_Ref[PI]', 'length[PI]'])

        # Get related CashAllocation records
        cash_allocations = CashAllocation.objects.filter(
            policy_fk_id__in=df_policies['pi_id'] if not df_policies.empty else [], archived=False
        ).values(
            'id',
            'policy_id',
            'policy_fk_id'
        ).annotate(
            ref_length=Length('policy_id')
        )

        # Convert to DataFrame
        df_allocations = pd.DataFrame(list(cash_allocations))
        if not df_allocations.empty:
            df_allocations.columns = ['ca_id', 'policy_id[CA]', 'policy_fk_id', 'length[CA]']
            df_allocations.to_csv('cash_allocations.csv', index=False)
        else:
            df_allocations = pd.DataFrame(columns=['ca_id', 'policy_id[CA]', 'policy_fk_id', 'length[CA]'])
        # Get related CashTrackerReport records
        cash_trackers = CashTrackerReport.objects.filter(
            cash_allocation_id__in=df_allocations['ca_id'] if not df_allocations.empty else []
        ).values(
            'id',
            'Policy',
            'cash_allocation_id'
        ).annotate(
            ref_length=Length('Policy')
        )

        # Convert to DataFrame
        df_trackers = pd.DataFrame(list(cash_trackers))
        if not df_trackers.empty:
            df_trackers.columns = ['ctr_id', 'Policy[CTR]', 'cash_allocation_id', 'length[CTR]']
        else:
            df_trackers = pd.DataFrame(columns=['ctr_id', 'Policy[CTR]', 'cash_allocation_id', 'length[CTR]'])
        # Merge all DataFrames
        result_df = df_allocations.merge(
            df_trackers,
            left_on='ca_id',
            right_on='cash_allocation_id',
            how='left'
        ).merge(
            df_policies,
            left_on='policy_fk_id',
            right_on='pi_id',
            how='left'
        )

        # Select and reorder columns
        final_columns = [
            'ca_id', 'policy_id[CA]', 'length[CA]',
            'ctr_id', 'Policy[CTR]', 'length[CTR]',
            'pi_id', 'Policy_Line_Ref[PI]', 'length[PI]'
        ]
        result_df = result_df[final_columns]

        # Export to CSV
        result_df.to_csv('combined_policy_data.csv', index=False)

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Found:\n'
                f'- {len(df_allocations)} cash allocations\n'
                f'- {len(df_trackers)} related cash tracker records\n'
                f'- {len(df_policies)} related policy information records\n'
                f'Data exported to combined_policy_data.csv'
            )
        )

        # Print sample of combined data
        self.stdout.write("\nFirst few records from combined dataset:")
        self.stdout.write(str(result_df.head()))

    def update_records(self):
        try:
            df = pd.read_csv('combined_policy_data.csv')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('Error: combined_policy_data.csv not found. Run collect_plc first.'))
            return

        updates = {
            'cash_allocations': 0,
            'cash_trackers': 0,
            'policy_info': 0
        }
        
        # Initialize separate lists for each type of change
        ca_changes = []
        ctr_changes = []
        pi_changes = []

        correct_policies = {
            'PWT00003421AB': 'PWT0000321AB',
            'PMT00002821AA': 'PMT0000221AA',
            'MFI10002821AA': 'MFI0002821AA',
            'PWT000321AB': 'PWT0000321AB'
        }

        # Bulk fetch records to reduce database queries
        ca_ids = df['ca_id'].dropna().unique()
        ctr_ids = df['ctr_id'].dropna().unique()
        pi_ids = df['pi_id'].dropna().unique()

        cash_allocations = {ca.id: ca for ca in CashAllocation.objects.filter(id__in=ca_ids, archived=False)}
        cash_trackers = {ctr.id: ctr for ctr in CashTrackerReport.objects.filter(id__in=ctr_ids)}
        policy_infos = {pi.id: pi for pi in PolicyInformation.objects.filter(id__in=pi_ids)}

        # Process CashAllocation records
        for ca_id in ca_ids:
            ca = cash_allocations.get(ca_id)
            if not ca or not ca.policy_id:
                continue

            if ca.policy_id in correct_policies:
                new_policy = correct_policies[ca.policy_id]
            else:
                new_policy = ca.policy_id.strip()
                if new_policy == ca.policy_id:
                    continue

            ca_changes.append({
                'ca_id': ca_id,
                'old_policy': ca.policy_id,
                'new_policy': new_policy,
                'old_length': len(ca.policy_id),
                'new_length': len(new_policy)
            })
            ca.policy_id = new_policy
            ca.save(update_fields=['policy_id'])
            updates['cash_allocations'] += 1

        # Process CashTrackerReport records
        for ctr_id in ctr_ids:
            ctr = cash_trackers.get(ctr_id)
            if not ctr or not ctr.Policy:
                continue

            if ctr.Policy in correct_policies:
                new_policy = correct_policies[ctr.Policy]
            else:
                new_policy = ctr.Policy.strip()
                if new_policy == ctr.Policy:
                    continue

            ctr_changes.append({
                'ctr_id': ctr_id,
                'old_policy': ctr.Policy,
                'new_policy': new_policy,
                'old_length': len(ctr.Policy),
                'new_length': len(new_policy),
                'cash_allocation_id': ctr.cash_allocation_id
            })
            ctr.Policy = new_policy
            ctr.save(update_fields=['Policy'])
            updates['cash_trackers'] += 1

        # Process PolicyInformation records
        for pi_id in pi_ids:
            pi = policy_infos.get(pi_id)
            if not pi or not pi.Policy_Line_Ref:
                continue

            if pi.Policy_Line_Ref in correct_policies:
                new_policy = correct_policies[pi.Policy_Line_Ref]
            else:
                new_policy = pi.Policy_Line_Ref.strip()
                if new_policy == pi.Policy_Line_Ref:
                    continue

            pi_changes.append({
                'pi_id': pi_id,
                'old_policy': pi.Policy_Line_Ref,
                'new_policy': new_policy,
                'old_length': len(pi.Policy_Line_Ref),
                'new_length': len(new_policy)
            })
            pi.Policy_Line_Ref = new_policy
            pi.save(update_fields=['Policy_Line_Ref'])
            updates['policy_info'] += 1

        # Create Excel file with multiple sheets
        if any([ca_changes, ctr_changes, pi_changes]):
            with pd.ExcelWriter('policy_changes2.xlsx', engine='openpyxl') as writer:
                # Cash Allocations sheet
                if ca_changes:
                    pd.DataFrame(ca_changes).to_excel(writer, sheet_name='Cash_Allocations', index=False)
                
                # Cash Tracker Reports sheet
                if ctr_changes:
                    pd.DataFrame(ctr_changes).to_excel(writer, sheet_name='Cash_Trackers', index=False)
                
                # Policy Information sheet
                if pi_changes:
                    pd.DataFrame(pi_changes).to_excel(writer, sheet_name='Policy_Information', index=False)

            self.stdout.write(self.style.SUCCESS('Changes exported to policy_changes.xlsx'))

        # Print summary of updates
        self.stdout.write(
            self.style.SUCCESS(
                f'Updated records:\n'
                f'- Cash Allocations: {updates["cash_allocations"]}\n'
                f'- Cash Tracker Reports: {updates["cash_trackers"]}\n'
                f'- Policy Information: {updates["policy_info"]}'
            )
        )

    