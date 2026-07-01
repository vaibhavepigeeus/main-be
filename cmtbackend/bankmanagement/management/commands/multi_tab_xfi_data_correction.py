'''
Class to update cash allocation and policy info details
    -> python manage.py multi_tab_xfi_data_correction --type 'Save' --tab 'Entity'

Note : Type will only be passed if you want to replace data
'''

from django.core.management.base import BaseCommand
import pandas as pd
import logging
import os
import openpyxl
from datetime import datetime

from bankmanagement.models import CashAllocation, CashTrackerReport, CashAllocaionAudit
from documents.models import PolicyInformation

logger = logging.getLogger(__name__)

TAB_CONFIG = {
    "Entity": {
        "excel_columns": ["Producing Coverholder - Entity", "XFI Producing Entity*", "Entity True/ False*", "Cash Allocation ID"],
        "condition_column": "Entity True/ False*",
        "condition_value": False,
        "ca": {"field": "allocation_entity", "excel": "XFI Producing Entity*"},
        "ctr": {"field": "Producing_Coverholder", "excel": "XFI Producing Entity*"},
        "pi": {"field": "Producing_Entity", "excel": "XFI Producing Entity*"},
    },
    "3rd Capacity": {
        "excel_columns": ["Third Party Capacity", "Third Party Capacity XFI*", "3rd Capacity True/ False*", "Cash Allocation ID"],
        "condition_column": "3rd Capacity True/ False*",
        "condition_value": False,
        "ca": {"field": "Third_Party_Capacity_", "excel": "Third Party Capacity XFI*"},
        "ctr": {"field": "Third_Party_Capacity", "excel": "Third Party Capacity XFI*"},
        "pi": {"field": "Three_Party_Capacity_Deployed", "excel": "Third Party Capacity XFI*"},
    },
    "MOP": {
        "excel_columns": ["MOP", "MOP XFI*", "MOP True/ False*", "Cash Allocation ID"],
        "condition_column": "MOP True/ False*",
        "condition_value": False,
        "ca": {"field": "MOP_", "excel": "MOP XFI*"},
        "ctr": {"field": "MOP_", "excel": "MOP XFI*"},
        "pi": {"field": "MOP", "excel": "MOP XFI*"},
    },
    "YOA": {
        "excel_columns": ["YOA", "YOA XFI*", "YOA True/ False*", "Cash Allocation ID"],
        "condition_column": "YOA True/ False*",
        "condition_value": False,
        "ca": {"field": "YOA_", "excel": "YOA XFI*"},
        "ctr": {"field": "YOA", "excel": "YOA XFI*"},
        "pi": {"field": "Year_of_Account", "excel": "YOA XFI*"},
    },
    "Syndicate Binder": {
        "excel_columns": ["Syndicate Binder", "Syndicate Binder XFI*", "Syndicate Binder True/ False*", "Cash Allocation ID"],
        "condition_column": "Syndicate Binder True/ False*",
        "condition_value": False,
        "ca": {"field": "allocation_binder", "excel": "Syndicate Binder XFI*"},
        "ctr": {"field": "Master_Binder", "excel": "Syndicate Binder XFI*"},
        "pi": {"field": "Syndicate_Binder", "excel": "Syndicate Binder XFI*"},
    },
    # "Broker": {
    #     "excel_columns": ["Broker*", "Broker XFI*", "Broker True/ False*", "Cash Allocation ID"],
    #     "condition_column": "Broker True/ False*",
    #     "condition_value": False,
    #     "ca": {"field": "Broker_", "excel": "Broker XFI*"},
    #     "ctr": {"field": "Broker", "excel": "Broker XFI*"},
    #     "pi": {"field": "Broker", "excel": "Broker XFI*"},
    # },
    "UMR": {
        "excel_columns": ["UMR Number", "UMR Number XFI*", "UMR True/ False*", "Cash Allocation ID"],
        "condition_column": "UMR True/ False*",
        "condition_value": False,
        "ca": {"field": "allocation_umr", "excel": "UMR Number XFI*"},
        "ctr": {"field": "UMR_Number_", "excel": "UMR Number XFI*"},
        "pi": {"field": "UMR_Number", "excel": "UMR Number XFI*"},
    },
    "Orig Currency": {
        "excel_columns": ["Original Currency", "Original Currency XFI*", "Orig Currency True/ False*", "Cash Allocation ID"],
        "condition_column": "Orig Currency True/ False*",
        "condition_value": False,
        "ca": {"field": "original_ccy", "excel": "Original Currency XFI*"},
        "ctr": {"field": "original_ccy_", "excel": "Original Currency XFI*"},
        "pi": {"field": "Original_Ccy", "excel": "Original Currency XFI*"},
    },
    "Settlement Currency": {
        "excel_columns": ["Settlement Currency Code", "Settlement Currency Code XFI*", "Settlement Currency True/ False*", "Cash Allocation ID"],
        "condition_column": "Settlement Currency True/ False*",
        "condition_value": False,
        "ca": {"field": "settlement_ccy", "excel": "Settlement Currency Code XFI*"},
        "ctr": {"field": "settlement_ccy_", "excel": "Settlement Currency Code XFI*"},
        "pi": {"field": "Settlement_Ccy", "excel": "Settlement Currency Code XFI*"},
    },
    "Policy Status": {
        "excel_columns": ["Policy Status", "Policy Status XFI*", "Policy Status True/ False*", "Cash Allocation ID"],
        "condition_column": "Policy Status True/ False*",
        "condition_value": False,
        "ca": {"field": "Policy_Status_", "excel": "Policy Status XFI*"},
        "ctr": {"field": "Policy_Status_", "excel": "Policy Status XFI*"},
        "pi": {"field": "Policy_Status", "excel": "Policy Status XFI*"},
    }
}

class Command(BaseCommand):
    help = 'Update Tabwise data in Policy Information, Cash Allocation and Cash Tracker Table'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, help='Type of operation to perform: create excel or create excel and save data')
        parser.add_argument('--tab', type=str, help='mention tab name which details you want to update')
        parser.add_argument('--user', type=str, help='User who is making the changes (for audit logging)')
    
    def handle(self, *args, **options):
        operation_type = options.get('type', 'normal')
        tab_value = options.get('tab', None)
        self.user = options.get('user', 'Script Updates')
        if tab_value and tab_value.lower() == 'all':
            for tab in TAB_CONFIG.keys():
                self.process_tab(operation_type, tab)
        else:
            self.process_tab(operation_type, tab_value)

    def process_tab(self, operation_type: str, tab_value: str):
        print(f"tab name: {tab_value}")
        logger.info(f"tab name: {tab_value}")
        excel_file_path = 'tabwise-data-correction.xlsx'
        audit_data = []

        config = TAB_CONFIG.get(tab_value)
        if not config:
            logger.info("Please provide a valid tab name.")
            print("Please provide a valid tab name.")
            return

        # Try reading with different headers
        for header in [2, 3]:
            try:
                df = pd.read_excel(
                    excel_file_path,
                    sheet_name=tab_value,
                    usecols=config["excel_columns"],
                    header=header
                )
                break
            except ValueError:
                continue
        else:
            logger.error("Failed to read Excel sheet with expected headers.")
            return

        for index, row in df.iterrows():
            if row[config["condition_column"]] != config["condition_value"]:
                continue

            row_audit = {}
            ca_obj = None

            for model_key, model_class, obj_getter in [
                ("ca", CashAllocation, lambda row: CashAllocation.objects.get(id=int(row['Cash Allocation ID']))),
                ("ctr", CashTrackerReport, lambda row: CashTrackerReport.objects.get(cash_allocation_id=int(row['Cash Allocation ID']))),
                ("pi", PolicyInformation, lambda row: CashAllocation.objects.get(id=int(row['Cash Allocation ID'])).policy_fk),
            ]:
                if model_key not in config:
                    continue

                field = config[model_key]["field"]
                excel_col = config[model_key]["excel"]
                new_value = row[excel_col]
                old_value = None
                obj = None
                error = ""
                obj_id = None

                try:
                    obj = obj_getter(row)
                    if model_key == "ca":
                        ca_obj = obj
                    # Check if the field exists on the object
                    if not hasattr(obj, field):
                        error = f"No field named '{field}' in {model_key.upper()} model"
                        old_value = None
                        new_value = None
                    else:
                        old_value = getattr(obj, field, None)
                        if model_key == "ca":
                            obj_id = row['Cash Allocation ID']  # Always use row value for ca id
                        else:
                            obj_id = getattr(obj, "id", None)
                        if operation_type == 'Save':
                            setattr(obj, field, new_value)
                            obj.save()
                            # Create audit record for CashAllocation changes
                            if model_key == "ca" and ca_obj:
                                CashAllocaionAudit.objects.create(
                                    cash_allocation=ca_obj,
                                    audit_data={
                                        "field_name": field,
                                        "old_value": old_value,
                                        "new_value": new_value,
                                        "previous_edit_datetime": ca_obj.updated_at.strftime("%Y-%m-%d %H:%M:%S") if ca_obj.updated_at else "-",
                                        "current_edit_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "changed_by": self.user,
                                        "event_type": "edit"
                                    }
                                )
                except Exception as e:
                    error = str(e)
                    if model_key == "ca":
                        obj_id = row['Cash Allocation ID']
                    else:
                        obj_id = None

                # Use the field name for the tab (e.g., 'yoa')
                tab_field = field.rstrip('_').lower()
                row_audit[f"{model_key} id"] = obj_id
                row_audit[f"old {model_key} {tab_field}"] = old_value
                row_audit[f"new {model_key} {tab_field}"] = new_value
                row_audit[f"{model_key} error"] = error

            audit_data.append(row_audit)

        # Write audit log
        audit_data_df = pd.DataFrame(audit_data)
        excel_output_path = "tabwise_update.xlsx"

        if os.path.exists(excel_output_path):
            # Load the workbook and check for the sheet
            wb = openpyxl.load_workbook(excel_output_path)
            if tab_value in wb.sheetnames:
                # Remove the sheet
                std = wb[tab_value]
                wb.remove(std)
                wb.save(excel_output_path)
            wb.close()

        # Now write the new sheet (append mode, since file may have other sheets)
        with pd.ExcelWriter(excel_output_path, engine="openpyxl", mode="a" if os.path.exists(excel_output_path) else "w") as writer:
            audit_data_df.to_excel(writer, sheet_name=tab_value, index=False)

        self.stdout.write(self.style.SUCCESS(f'Successfully exported {tab_value} data to tabwise_update.xlsx'))