'''
Class to update cash allocation, ctr and policy info details
    -> python manage.py pi_ca_ctr_data_correction --type 'save_details' --batch_size 500 --changed_by "User Name"

Note :
- Type will only be passed if you want to replace data
- changed_by is optional, defaults to "Script Updates" if not provided
'''

from django.core.management.base import BaseCommand
import pandas as pd
import logging
from django.db import transaction
import os
from datetime import datetime

from bankmanagement.models import CashAllocation, CashTrackerReport, CashAllocaionAudit
from documents.models import PolicyInformation

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update Original Amount in Policy Information Table'

    def add_arguments(self, parser):
        # Adding new command line arguments
        parser.add_argument('--type', type=str, help='Type of operation to perform: create excel or create excel and save data')
        parser.add_argument('--batch_size', type=int, default=500, help='Number of records to process in each batch')
        parser.add_argument('--limit', type=int, default=None, help='Limit the total number of records to process')
        parser.add_argument('--changed_by', type=str, default="Script Updates", help='Name of the user making the changes')

    def handle(self, **options):
        operation_type = options.get('type', 'normal')
        batch_size = options.get('batch_size', 500)
        limit = options.get('limit')
        changed_by = options.get('changed_by', 'Script Updates')
        self.update_data(operation_type, batch_size, limit, changed_by)

    def update_data(self, operation_type: str, batch_size: int = 500, limit: int = None, changed_by: str = "Script Updates"):
        logger.info("Updating Policy and CashAllocation Data")
        self.stdout.write(self.style.SUCCESS("Starting data correction process..."))
        self.stdout.write(f"Changes will be attributed to: {changed_by}")

        start_time = datetime.now()
        audit_data = []

        try:
            # Get total count for progress bar
            total_records = CashAllocation.objects.count()
            if limit:
                total_records = min(total_records, limit)

            self.stdout.write(f"Processing {total_records} records in batches of {batch_size}")

            # Process in batches
            offset = 0
            while offset < total_records:
                current_batch_size = min(batch_size, total_records - offset)
                self.stdout.write(f"Processing batch {offset//batch_size + 1} ({offset} to {offset + current_batch_size})")

                # Get the current batch of CashAllocation objects with prefetched policy_fk
                cash_allocations = CashAllocation.objects.select_related('policy_fk').order_by("-id")[offset:offset + current_batch_size]

                # Process each record in the batch
                batch_audit_data = self.process_batch(cash_allocations, operation_type, changed_by)
                audit_data.extend(batch_audit_data)

                offset += current_batch_size

            # Create the final DataFrame
            if audit_data:
                audit_data_df = pd.DataFrame(audit_data)

                # Move 'Error' column to the last position
                if 'Error' in audit_data_df.columns:
                    error_col = audit_data_df.pop('Error')
                    audit_data_df['Error'] = error_col

                # Create output directory if it doesn't exist
                output_dir = "data_correction_reports"
                os.makedirs(output_dir, exist_ok=True)

                # Save audit data to Excel
                output_file = "pi_ca_ctr_data_correction.xlsx"
                audit_data_df.to_excel(output_file, index=False)
                self.stdout.write(self.style.SUCCESS(f"DataFrame has been successfully exported to {output_file}"))
            else:
                self.stdout.write(self.style.WARNING("No data was processed or updated."))

        except Exception as e:
            logger.error(f"Error in update_data: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

        elapsed_time = datetime.now() - start_time
        self.stdout.write(self.style.SUCCESS(f"Process completed in {elapsed_time}"))

    def process_batch(self, cash_allocations, operation_type, changed_by="Script Updates"):
        """Process a batch of CashAllocation records"""
        batch_audit_data = []

        # Collect policy_fk IDs for bulk query
        policy_ids = [ca.policy_fk.pk for ca in cash_allocations if ca.policy_fk]
        policy_numbers = [ca.policy_id for ca in cash_allocations if ca.policy_id]

        # Prefetch related PolicyInformation objects
        policy_info_map = {pi.id: pi for pi in PolicyInformation.objects.filter(id__in=policy_ids)}
        policy_line_ref_map = {pi.Policy_Line_Ref: pi for pi in PolicyInformation.objects.filter(
            archived=False, Policy_Line_Ref__in=policy_numbers
        )}

        # Prepare lists for bulk updates
        policies_to_update = []
        cash_allocations_to_update = []
        ctr_to_update = []
        # Process each CashAllocation
        for i in cash_allocations:
            audit_row = {}
            update = False
            obj = None

            try:
                # Get the related PolicyInformation object
                j = policy_info_map.get(i.policy_fk.pk)

                if not j:
                    logger.warning(f"PolicyInformation not found for CashAllocation {i.pk}")
                    continue

                if j.Class_of_Business is None:
                    # Find matching policy by Policy_Line_Ref
                    obj = policy_line_ref_map.get(i.policy_id)

                    if obj and obj.Policy_Line_Ref != "nan":
                        update = True
                        Three_Party_Capacity_Deployed = obj.Three_Party_Capacity_Deployed
                        if Three_Party_Capacity_Deployed == "No":
                            binding_agreement = "NON-SCM"
                        else:
                            binding_agreement = "SCM"

                        # Add all details to a row dictionary
                        audit_row = {
                            "Policy ID": j.pk,
                            "Policy Number": j.Policy_Line_Ref,
                            "PI old Producing Entity": j.Producing_Entity,
                            "PI new Producing Entity": obj.Producing_Entity,
                            "PI old Broker": j.Broker,
                            "PI new Broker": obj.Broker,
                            "PI old UMR_Number": j.UMR_Number,
                            "PI new UMR_Number": obj.UMR_Number,
                            "PI old Binding_Agreement": j.Binding_Agreement,
                            "PI new Binding_Agreement": binding_agreement,
                            "PI old SCM_Partner": j.SCM_Partner,
                            "PI new SCM_Partner": obj.SCM_Partner,
                            "PI old MOP": j.MOP,
                            "PI new MOP": obj.MOP,
                            "PI old Year_of_Account": j.Year_of_Account,
                            "PI new Year_of_Account": obj.Year_of_Account,
                            "PI old Syndicate_Binder": j.Syndicate_Binder,
                            "PI new Syndicate_Binder": obj.Syndicate_Binder,
                            "PI old Insured": j.Insured,
                            "PI new Insured": obj.Insured,
                            "PI old Settlement_Ccy": j.Settlement_Ccy,
                            "PI new Settlement_Ccy": obj.Settlement_Ccy,
                            "PI old Three_Party_Capacity_Deployed": j.Three_Party_Capacity_Deployed,
                            "PI new Three_Party_Capacity_Deployed": Three_Party_Capacity_Deployed,
                        }

                        # Update PolicyInformation fields
                        j.Producing_Entity = obj.Producing_Entity
                        j.Broker = obj.Broker
                        j.UMR_Number = obj.UMR_Number
                        j.Binding_Agreement = binding_agreement
                        j.SCM_Partner = obj.SCM_Partner
                        j.MOP = obj.MOP
                        j.Year_of_Account = obj.Year_of_Account
                        j.Syndicate_Binder = obj.Syndicate_Binder
                        j.Insured = obj.Insured
                        j.Settlement_Ccy = obj.Settlement_Ccy
                        j.Three_Party_Capacity_Deployed = Three_Party_Capacity_Deployed

                        # Add to list for bulk update
                        policies_to_update.append(j)
                    else:
                        if obj:
                            audit_row['Error'] = f"Policy Details not found in Policy Information file with Policy id: {obj.pk} and Policy number: {obj.Policy_Line_Ref}"
                        else:
                            audit_row['Error'] = f"Policy Details not found in Policy Information file with Policy id: {j.pk} and Policy number: {j.Policy_Line_Ref}"
                else:
                    audit_row['Error'] = "Policy's Class_of_Business is not none"

            except Exception as e:
                logger.error(f"Error processing PolicyInformation for CashAllocation {i.pk}: {str(e)}", exc_info=True)
                audit_row.update({'PI Error': str(e)})

            # Update CashAllocation if needed
            try:
                if update and obj:
                    update_dict = {
                        "CA old allocation_entity": i.allocation_entity,
                        "CA new allocation_entity": obj.Producing_Entity,
                        "CA old allocation_umr": i.allocation_umr,
                        "CA new allocation_umr": obj.UMR_Number,
                        "CA old binding_agreement": i.binding_agreement,
                        "CA new binding_agreement": binding_agreement,
                        "CA old allocation_binder": i.allocation_binder,
                        "CA new allocation_binder": obj.Syndicate_Binder,
                    }
                    audit_row.update(update_dict)

                    # Save cashalllocation audit if operation_type is 'save_details'
                    if operation_type == "save_details":
                        for key, value in update_dict.items():
                            if "old" in key:
                                old_value = value
                                field_name = key.replace("CA old ", "")
                            else:
                                new_value = value

                        CashAllocaionAudit.objects.create(
                            cash_allocation=i,
                            audit_data={
                                "field_name": field_name,
                                "old_value": old_value,
                                "new_value": new_value,
                                "previous_edit_datetime": i.updated_at.strftime("%Y-%m-%d %H:%M:%S") if i.updated_at else "-",
                                "current_edit_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "changed_by": changed_by,
                                "event_type": "edit"
                            }
                        )

                    i.allocation_entity = obj.Producing_Entity
                    i.allocation_umr = obj.UMR_Number
                    i.binding_agreement = binding_agreement
                    i.allocation_binder = obj.Syndicate_Binder

                    # Add to list for bulk update
                    cash_allocations_to_update.append(i)
            except Exception as e:
                logger.error(f"Error updating CashAllocation {i.pk}: {str(e)}", exc_info=True)
                audit_row.update({'CA Error': str(e)})

            # Update CashTrackerReport if needed
            try:
                if update and obj:
                    # Use select_related to get the related CashTrackerReport in a single query
                    k = CashTrackerReport.objects.filter(cash_allocation=i).first()
                    if k:
                        audit_row.update({
                            "CTR old Binding_Agreement": k.Binding_Agreement,
                            "CTR new Binding_Agreement": binding_agreement,
                            "CTR old SCM_Partners": k.SCM_Partners,
                            "CTR new SCM_Partners": obj.SCM_Partner,
                            "CTR old Master_Binder": k.Master_Binder,
                            "CTR new Master_Binder": obj.Syndicate_Binder,
                            "CTR old Third_Party_Capacity": k.Third_Party_Capacity,
                            "CTR new Third_Party_Capacity": Three_Party_Capacity_Deployed,
                        })

                        k.Binding_Agreement = binding_agreement
                        k.SCM_Partners = obj.SCM_Partner
                        k.Master_Binder = obj.Syndicate_Binder
                        k.Third_Party_Capacity = Three_Party_Capacity_Deployed

                        # Add to list for bulk update
                        ctr_to_update.append(k)
            except Exception as e:
                logger.error(f"Error updating CashTrackerReport for CashAllocation {i.pk}: {str(e)}", exc_info=True)
                audit_row.update({'CTR Error': str(e)})

            # Append the audit_row to the batch_audit_data list
            if bool(audit_row):
                batch_audit_data.append(audit_row)

        # Perform bulk updates if operation_type is 'save_details'
        if operation_type == "save_details" and (policies_to_update or cash_allocations_to_update or ctr_to_update):
            with transaction.atomic():
                try:
                    # Bulk update PolicyInformation objects
                    if policies_to_update:
                        fields_to_update = [
                            'Producing_Entity', 'Broker', 'UMR_Number', 'Binding_Agreement',
                            'SCM_Partner', 'MOP', 'Year_of_Account', 'Syndicate_Binder',
                            'Insured', 'Settlement_Ccy', 'Three_Party_Capacity_Deployed'
                        ]
                        PolicyInformation.objects.bulk_update(policies_to_update, fields_to_update)
                        logger.info(f"Updated {len(policies_to_update)} PolicyInformation records")

                    # Bulk update CashAllocation objects
                    if cash_allocations_to_update:
                        fields_to_update = [
                            'allocation_entity', 'allocation_umr', 'binding_agreement', 'allocation_binder'
                        ]
                        CashAllocation.objects.bulk_update(cash_allocations_to_update, fields_to_update)
                        logger.info(f"Updated {len(cash_allocations_to_update)} CashAllocation records")

                    #

                    # Bulk update CashTrackerReport objects
                    if ctr_to_update:
                        fields_to_update = [
                            'Binding_Agreement', 'SCM_Partners', 'Master_Binder', 'Third_Party_Capacity'
                        ]
                        CashTrackerReport.objects.bulk_update(ctr_to_update, fields_to_update)
                        logger.info(f"Updated {len(ctr_to_update)} CashTrackerReport records")
                except Exception as e:
                    logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
                    # Transaction will be rolled back automatically
                    raise

        return batch_audit_data
