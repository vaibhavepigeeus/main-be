from django.core.management.base import BaseCommand
from openpyxl import Workbook
import os
from bankmanagement.models import CashAllocaionAudit
from users.models import Users

class Command(BaseCommand):
    help = 'Update user id and user name'

    def add_arguments(self, parser):
        # Adding new command line arguments
        parser.add_argument('--type', type=str, help='Type of operation to perform: create excel or create excel and save data')

    def handle(self, *args, **kwargs):
        operation_type = kwargs.get('type', 'normal')
        print("operation_type", operation_type)
        # Create a workbook and sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Cash allocation Audit"

        # Headers
        headers = [
            'changed by old',
            'changed by new',
        ]
        ws.append(headers)

        data = CashAllocaionAudit.objects.values_list('id', 'audit_data')
        print("data count", data.count())

        for i,j in data:
            obj = CashAllocaionAudit.objects.get(id=i)
            dict_data = dict(j)
            if type(dict_data['changed_by']) == str:
                append_data = []
                append_data.append(dict_data['changed_by'])
                user_data = Users.objects.filter(user_name=dict_data['changed_by'])
                if user_data.exists():
                    active_user_data = user_data.filter(status="Active")
                    if active_user_data:
                        append_data.append(active_user_data.last().id)
                        if operation_type == 'Save':
                            dict_data['changed_by'] = active_user_data.last().id
                            dict_data['changed_by_username'] = active_user_data.last().user_name
                            obj.audit_data = dict_data
                            obj.save()
                    else:
                        append_data.append(user_data.last().id)
                else:
                    append_data.append('')
                ws.append(append_data)
            else:
                if operation_type == 'Save':
                    dict_data['changed_by_username'] = Users.objects.filter(id=dict_data['changed_by']).last().user_name
                    obj.audit_data = dict_data
                    obj.save()
                
        # Save the file
        wb.save('ca_audit.xlsx')

        self.stdout.write(self.style.SUCCESS(f'Successfully exported ca audit data to ca_audit.xlsx'))