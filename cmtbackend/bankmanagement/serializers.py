from rest_framework import serializers
from .models import *
from django.db.models import Sum
from users.utils import get_masked_email
from users.serializers import MinimalUserSerializer
from datetime import datetime, timedelta
from users.models import Users
from django.utils import timezone

class BankReconciliationSerializer(serializers.ModelSerializer):
    allocated_analyst_id = MinimalUserSerializer(read_only=True)
    uploaded_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = BankReconciliation
        fields = '__all__'
        depth = 1

class BankTransactionSerializer(serializers.ModelSerializer):
    Assigned_User = MinimalUserSerializer(read_only=True)
    Assigned_Users = MinimalUserSerializer(many=True, read_only=True)
    bank_reconciliation = BankReconciliationSerializer(read_only=True)

    class Meta:
        model = BankTransaction
        fields = '__all__'
        depth = 2
    
    # CMT-28
    def to_representation(self, instance):
        data = super().to_representation(instance)
        total = CashAllocation.objects.filter(bank_txn=instance.id, allocation_status="Allocated", archived=False).aggregate(
            total_allocated=Sum('allocated_amt')
        )['total_allocated'] or 0
        data['total_allocated'] = total

        audit_list = []
        for row in BankTransactionAudit.objects.filter(bank_transaction=instance):
            current_time = datetime.strptime(row.audit_data['current_edit_datetime'], "%Y-%m-%d %H:%M:%S")
            
            # Handle case where previous_edit_datetime is "-"
            if row.audit_data['previous_edit_datetime'] == "-":
                time_diff_seconds = 0  # No previous time, so difference is 0
            else:
                previous_time = datetime.strptime(row.audit_data['previous_edit_datetime'], "%Y-%m-%d %H:%M:%S")
                time_diff_seconds = (current_time - previous_time).total_seconds()
            
            days = int(time_diff_seconds // 86400)
            hours = int((time_diff_seconds % 86400) // 3600)
            minutes = int((time_diff_seconds % 3600) // 60)
            seconds = int(time_diff_seconds % 60)
            
            # Format time difference with days if needed
            if days > 0:
                time_diff_str = f"{days:02d} days {hours:02d} hours {minutes:02d} minutes {seconds:02d} seconds"
            else:
                time_diff_str = f"{hours:02d} hours {minutes:02d} minutes {seconds:02d} seconds"
                
            audit_list.append({
                "field_name": row.audit_data['field_name'], 
                "old_value": row.audit_data['old_value'], 
                "new_value": row.audit_data['new_value'], 
                "changed_by": row.audit_data['changed_by'] if type(row.audit_data['changed_by'])==str else Users.objects.get(id=row.audit_data['changed_by']).user_name, 
                "current_edit_datetime": row.audit_data['current_edit_datetime'], 
                "previous_edit_datetime": row.audit_data['previous_edit_datetime'], 
                "time_diff": time_diff_str if row.audit_data['event_type'] == "edit" else "-",
                "event_type": row.audit_data['event_type']
            })
        data['bank_transaction_audit_data'] = audit_list

        return data
    
class CashAllocationSerializer(serializers.ModelSerializer):
    remaining_balance = serializers.SerializerMethodField()
    policy_original_amount_list = serializers.SerializerMethodField(read_only=True)
    locked_by = MinimalUserSerializer(read_only=True)
    created_by = MinimalUserSerializer(read_only=True)
    updated_by = MinimalUserSerializer(read_only=True)
    bank_txn = BankTransactionSerializer(read_only=True)
    policy_handler = MinimalUserSerializer(read_only=True)

    class Meta:
        model = CashAllocation
        fields = '__all__'
        depth = 3

    def get_remaining_balance(self, obj):
        remaining_balance = obj.receivable_amt - obj.allocated_amt if obj.receivable_amt is not None else None
        return remaining_balance

    def get_policy_original_amount_list(self, obj):
        # Return the policy information dictionary if it exists in the object
        return obj.policy_original_amount_list if hasattr(obj, 'policy_original_amount_list') else None
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        allocation_status_editable = False
        try:
            obj = AccountingMonthEnd.objects.get(accounting_month_date=instance.accounting_monthyear)
            if obj.accounting_month_start_date <= instance.allocation_date <= obj.accounting_month_end_date:
                allocation_status_editable = True
        except:
            pass
        data['allocation_status_editable'] = allocation_status_editable

        audit_list = []
        for row in CashAllocaionAudit.objects.filter(cash_allocation=instance):
            current_time = datetime.strptime(row.audit_data['current_edit_datetime'], "%Y-%m-%d %H:%M:%S")
            
            # Handle case where previous_edit_datetime is "-"
            if row.audit_data['previous_edit_datetime'] == "-":
                time_diff_seconds = 0  # No previous time, so difference is 0
            else:
                previous_time = datetime.strptime(row.audit_data['previous_edit_datetime'], "%Y-%m-%d %H:%M:%S")
                time_diff_seconds = (current_time - previous_time).total_seconds()
            
            days = int(time_diff_seconds // 86400)
            hours = int((time_diff_seconds % 86400) // 3600)
            minutes = int((time_diff_seconds % 3600) // 60)
            seconds = int(time_diff_seconds % 60)
            
            # Format time difference with days if needed
            if days > 0:
                time_diff_str = f"{days:02d} days {hours:02d} hours {minutes:02d} minutes {seconds:02d} seconds"
            else:
                time_diff_str = f"{hours:02d} hours {minutes:02d} minutes {seconds:02d} seconds"
                
            audit_list.append({
                "field_name": row.audit_data['field_name'], 
                "old_value": row.audit_data['old_value'], 
                "new_value": row.audit_data['new_value'], 
                "changed_by": row.audit_data['changed_by'] if type(row.audit_data['changed_by']) == str else Users.objects.get(id=row.audit_data['changed_by']).user_name, 
                "current_edit_datetime": row.audit_data['current_edit_datetime'], 
                "previous_edit_datetime": row.audit_data['previous_edit_datetime'], 
                "time_diff": time_diff_str if row.audit_data['event_type'] == "edit" else "-",
                "event_type": row.audit_data['event_type']
            })
        data['cash_allocation_audit_data'] = audit_list
        return data


class BankTransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransaction
        fields = '__all__'


class CashAllocationIssuesSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = CashAllocationIssues
        fields = '__all__'
        depth = 3


class CashAllocationIssuesCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAllocationIssues
        fields = '__all__'


class CashAllocationCorrectiveSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = CashAllocationCorrective
        fields = '__all__'
        depth = 3


class CashAllocationCorrectiveCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAllocationCorrective
        fields = '__all__'


class CashAllocationWriteoffSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = CashAllocationWriteoff
        fields = '__all__'
        depth = 3


class CashAllocationWriteoffCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAllocationWriteoff
        fields = '__all__'


class CashAllocationRefundSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = CashAllocationRefund
        fields = '__all__'
        depth = 3


class CashAllocationRefundCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAllocationRefund
        fields = '__all__'


class CashAllocationCFISerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = CashAllocationCFI
        fields = '__all__'
        depth = 3


class CashAllocationCFICreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAllocationCFI
        fields = '__all__'


class CrossAllocationSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = CrossAllocation
        fields = '__all__'
        depth = 3


class CrossAllocationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossAllocation
        fields = '__all__'


class CashAllocationMSDSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = CashAllocationMSD
        fields = '__all__'
        depth = 3


class CashAllocationMSDCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAllocationMSD
        fields = '__all__'


class PremiumPaymentSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = PremiumPayment
        fields = '__all__'
        depth = 3


class PremiumPaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumPayment
        fields = '__all__'


class CorrectiveTRFSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveTRF
        fields = '__all__'
        depth = 3


class CorrectiveTRFCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveTRF
        fields = '__all__'


class CashAllocationCreateSerializer(serializers.ModelSerializer):
    policy_handler = MinimalUserSerializer(read_only=True)
    class Meta:
        model = CashAllocation
        fields = '__all__'

        # Override the required fields
        extra_kwargs = {
            'is_contra_allocation': {'required': False},  # Making is_contra_allocation optional
            'parent_contra_id': {'required': False},      # Making parent_contra_id optional
            'child_contra_id': {'required': False},       # Making child_contra_id optional
        }


class WorkStepCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkStep
        fields = '__all__'


class WorkStepSerializer(serializers.ModelSerializer):
    user = MinimalUserSerializer(many=True, read_only=True)
    class Meta:
        model = WorkStep
        fields = '__all__'
        depth = 2


class WorkFlowCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkFlow
        fields = '__all__'


class WorkFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkFlow
        fields = '__all__'
        depth = 3


class CashTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashTracker
        fields = '__all__'


class CashTrackerReportSerializer(serializers.ModelSerializer):
    created_by = MinimalUserSerializer(read_only=True)
    updated_by = MinimalUserSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)
    bank_txn = BankTransactionSerializer(read_only=True)
    ca_issues = CashAllocationIssuesSerializer(read_only=True)
    ca_corrective = CashAllocationCorrectiveSerializer(read_only=True)

    class Meta:
        model = CashTrackerReport
        fields = '__all__'


class WorkflowBankTransactionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowBankTransactions
        fields = '__all__'


class CashAllocationAllocatedTransaction(serializers.ModelSerializer):
    class Meta:
        model = CashAllocation
        fields = ('allocation_datetime', 'locked')  # Fields relevant to locking/unlocking


class CashAllocationLockedUnlockedHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for CashAllocationLockedUnlockedHistory model.
    """
    locked_unlocked_by_username = serializers.SerializerMethodField()
    locked_unlocked_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = CashAllocationLockedUnlockedHistory
        fields = '__all__'

    def get_locked_unlocked_by_username(self, obj):
        """
        Retrieve the username of the user who locked/unlocked the record.
        """
        return obj.locked_unlocked_by.user_name

class AccountingMonthEndSerializer(serializers.ModelSerializer):
    # created_by = MinimalUserSerializer(read_only=True)
    # updated_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = AccountingMonthEnd
        fields = '__all__'
    
    def validate_date_format(self, date):
        """
        Validate if the date is in the correct YYYY-MM-DD format.
        """
        try:
            return datetime.strptime(str(date), '%Y-%m-%d').date()
        except ValueError:
            raise serializers.ValidationError("Date must be in YYYY-MM-DD format")

    def check_overlap_and_gaps(self, new_start_date, new_end_date, instance=None):
        # Check overlaps
        overlap = AccountingMonthEnd.objects.filter(
            accounting_month_start_date__lte=new_end_date,
            accounting_month_end_date__gte=new_start_date
        ).exclude(id=getattr(instance, 'id', None))

        if overlap.exists():
            raise serializers.ValidationError(
                detail={"message": "Overlap detected with existing period(s)"}
            )

        # Check previous record
        prev_record = AccountingMonthEnd.objects.filter(
            accounting_month_end_date__lt=new_start_date
        ).order_by('-accounting_month_end_date').first()

        if prev_record and prev_record.id != getattr(instance, 'id', None):
            days_diff = (new_start_date - prev_record.accounting_month_end_date).days
            if days_diff != 1:
                raise serializers.ValidationError(
                    detail={"message": f"Gap detected with previous period ending on {prev_record.accounting_month_end_date.strftime('%d-%b-%Y')}"}
                )

        # Check next record
        next_record = AccountingMonthEnd.objects.filter(
            accounting_month_start_date__gt=new_end_date
        ).order_by('accounting_month_start_date').first()

        if next_record and next_record.id != getattr(instance, 'id', None):
            days_diff = (next_record.accounting_month_start_date - new_end_date).days
            if days_diff != 1:
                raise serializers.ValidationError(
                    detail={"message": f"Gap detected with next period starting on {next_record.accounting_month_start_date.strftime('%d-%b-%Y')}"}
                )
    
    def validate(self, data):
        """
        Perform all validations: date format, past dates, overlaps, and gaps.
        """
        if 'accounting_month_start_date' in data and 'accounting_month_end_date' in data:
            new_start_date = data['accounting_month_start_date']
            new_end_date = data['accounting_month_end_date']

            # Validate date formats
            self.validate_date_format(new_start_date)
            self.validate_date_format(new_end_date)

            # Ensure start date is before end date
            if new_start_date >= new_end_date:
                raise serializers.ValidationError("Start date must be before end date.")

            # Validate overlaps and gaps
            instance = self.instance if self.instance else None

            # Validate no past dates
            if instance:
                if (new_start_date < datetime.now().date() or new_end_date < datetime.now().date()):
                    raise serializers.ValidationError("Cannot modify past dates.")
            
            self.check_overlap_and_gaps(new_start_date, new_end_date, instance)

        return data
    

class ChaserSerializer(serializers.ModelSerializer):
    locked_by = MinimalUserSerializer(read_only=True)
    created_by = MinimalUserSerializer(read_only=True)
    updated_by = MinimalUserSerializer(read_only=True)
    bank_transaction = BankTransactionSerializer(read_only=True)
    cash_allocation = CashAllocationSerializer(read_only=True)

    class Meta:
        model = FollowUp
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        current_time = datetime.now()
        indicator_obj = ChaserIndicator.objects.all()

        if indicator_obj.count() < 1:
            green_to_yellow = 24
            yellow_to_red = 48
        else:
            green_to_yellow = indicator_obj.first().green_to_yellow
            yellow_to_red = indicator_obj.first().yellow_to_red
        data['followup_data'] = None
        data['indicator'] = "Green"
        db_time = current_time
        audit_list = []
        for row in FollowUpAudit.objects.filter(follow_up=instance):
            audit_current_time = datetime.strptime(row.audit_data['current_edit_datetime'], "%Y-%m-%d %H:%M:%S")
            
            # Handle case where previous_edit_datetime is "-"
            if row.audit_data['previous_edit_datetime'] == "-":
                time_diff_seconds = 0  # No previous time, so difference is 0
            else:
                previous_time = datetime.strptime(row.audit_data['previous_edit_datetime'], "%Y-%m-%d %H:%M:%S")
                time_diff_seconds = (audit_current_time - previous_time).total_seconds()
            
            days = int(time_diff_seconds // 86400)
            hours = int((time_diff_seconds % 86400) // 3600)
            minutes = int((time_diff_seconds % 3600) // 60)
            seconds = int(time_diff_seconds % 60)
            
            # Format time difference with days if needed
            if days > 0:
                time_diff_str = f"{days:02d} days {hours:02d} hours {minutes:02d} minutes {seconds:02d} seconds"
            else:
                time_diff_str = f"{hours:02d} hours {minutes:02d} minutes {seconds:02d} seconds"
                
            audit_list.append({
                "field_name": row.audit_data['field_name'], 
                "old_value": row.audit_data['old_value'], 
                "new_value": row.audit_data['new_value'], 
                "changed_by": row.audit_data['changed_by'] if type(row.audit_data['changed_by'])==str else Users.objects.get(id=row.audit_data['changed_by']).user_name, 
                "current_edit_datetime": row.audit_data['current_edit_datetime'], 
                "previous_edit_datetime": row.audit_data['previous_edit_datetime'], 
                "time_diff": time_diff_str if row.audit_data['event_type'] == "edit" else "-",
                "event_type": row.audit_data['event_type']
            })

        if instance.escalation_date_value:
            db_time = instance.escalation_date
        elif instance.date3_value:
            db_time = instance.date3
        elif instance.date2_value:
            db_time = instance.date2
        elif instance.date1_value:
            db_time = instance.date1

        # Ensure both datetimes are timezone-aware
        if timezone.is_naive(current_time):
            current_time = timezone.make_aware(current_time)
        if timezone.is_naive(db_time):
            db_time = timezone.make_aware(db_time)

        start = db_time
        end = current_time
        weekend_days = 0

        while start <= end:
            if start.weekday() >= 5: # 0-4 for Monday-Friday and 5-6 for Saturday-Sunday
                weekend_days += 1
            start = start + timedelta(days = 1)

        hours_diff = (current_time - db_time).total_seconds() / 3600
        hours_diff -= weekend_days*24

        if hours_diff <= int(green_to_yellow):
            indicator = 'Green'
        elif hours_diff <= int(yellow_to_red):
            indicator = 'Yellow'
        else:
            indicator = 'Red'
        data['indicator'] = indicator
        data['followup_audit_data'] = audit_list
        
        return data


class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = '__all__'


class BankTransactionSerilizerHelper(serializers.ModelSerializer):
    Assigned_User = MinimalUserSerializer(read_only=True)
    class Meta:
        model = BankTransaction
        fields = ['id', 'Bank_Transaction_Id', 'Assigned_User']


class PolicySerilizerHelper(serializers.ModelSerializer):
    class Meta:
        model = PolicyInformation
        fields = ['id', 'Policy_Line_Ref']


class AssignPolicyHandlerSerializer(serializers.ModelSerializer):
    bank_txn = BankTransactionSerilizerHelper(read_only=True)
    policy_handler = MinimalUserSerializer(read_only=True)
    policy_fk = PolicySerilizerHelper(read_only=True)
    class Meta:
        model = CashAllocation
        fields = ['id', 'policy_fk', 'allocation_status', 'bank_txn', 'receivable_amt', 'policy_handler', 'policy_assign_date']
