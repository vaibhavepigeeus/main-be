"""
Class to update historical policy info details
    -> python manage.py update_historical_policy_data --update 'true'

Note : 'update' will only be passed if you want to replace data
"""

import pandas as pd
from bankmanagement.models import CashAllocation
from django.core.management.base import BaseCommand
from documents.models import PolicyInformation


class Command(BaseCommand):
    """
    Class to update the historical Policy Information
    """

    help = "Class to update the historical Policy Information"

    def add_arguments(self, parser):
        # Adding new command line arguments
        parser.add_argument(
            "--update",
            type=str,
            help="Type of operation to perform: create excel or create excel and save data",
        )

    def handle(self, *args, **options):
        update_db_data: str = options.get("update", "false")
        self.update_policy_info(update_db_data)

    def update_policy_info(self, update_db_data: str = False):
        """
        Function to update the historical policy information data
        to match sync/correct data values for cash allocation
        """
        try:
            cash_allocations = CashAllocation.objects.filter(
                archived=False, policy_fk__Policy_Status__isnull=True
            )

            updated_records = []
            updated_count = 0
            for ca in cash_allocations:
                policy_fk_id = ca.policy_fk.id
                policy_info_for_fk = PolicyInformation.objects.filter(
                    id=policy_fk_id
                ).first()

                if policy_info_for_fk and policy_info_for_fk.Policy_Status is None:
                    # Extracting policy_id as per Referenced Policy
                    policy_id = ca.policy_id
                    if (
                        policy_info_for_fk.Policy_Line_Ref
                        and str(policy_info_for_fk.Policy_Line_Ref).lower() != "nan"
                    ):
                        policy_id = policy_info_for_fk.Policy_Line_Ref

                    # Fetching all the values
                    policy_infos = PolicyInformation.objects.filter(
                        Policy_Line_Ref=policy_id, Policy_Status__isnull=False
                    )

                    if policy_infos.count() > 1:
                        # Taking the latest added record
                        latest_policy = policy_infos.order_by("-id").first()

                        fields_to_update = [
                            "Policy_Line_Ref",
                            "SCM_Partner",
                            "Syndicate_Binder",
                            "Producing_Entity",
                            "UMR_Number",
                            "MOP",
                            "Three_Party_Capacity_Deployed",
                            "Class_of_Business",
                            "Year_of_Account",
                            "Broker",
                            "Master_Broker",
                            "Insured",
                            "Settlement_Ccy",
                            "Original_Ccy",
                        ]

                        update_fields = []
                        old_values = {}
                        new_values = {}
                        for field in fields_to_update:
                            update_fields.append(field)
                            old_value = getattr(policy_info_for_fk, field)
                            new_value = getattr(latest_policy, field)

                            setattr(policy_info_for_fk, field, new_value)
                            old_values[field] = old_value
                            new_values[field] = new_value

                        updated_count += 1
                        if update_db_data.lower() == "true":
                            policy_info_for_fk.save(update_fields=update_fields)
                            print(
                                f"Updated for CA-Id = {ca.id} -> PI-Id = {policy_info_for_fk.id}"
                            )

                        updated_records.append(
                            {
                                "Cash Allocation Id": ca.id,
                                "Policy FK ID": policy_info_for_fk.id,
                                "Policy Status": policy_info_for_fk.Policy_Status,
                                "Updated Fields": update_fields,
                                "Old Values": old_values,
                                "New Values": new_values,
                            }
                        )

                # Write audit information to CSV
                if updated_records:
                    df = pd.DataFrame(updated_records)
                    df.to_csv("policy_info_updates_audit.csv", index=False)

            print(f"Records updated {updated_count}")

        except Exception as e:
            print(f"Error while running script : {str(e)}")
