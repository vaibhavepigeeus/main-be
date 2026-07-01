from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from django.db import connection
from django.db.models import Q, Count, Sum,  F

from ..models import BankReconciliation, BankTransaction, \
    CashTracker, CashAllocation, CashTrackerReport, Users
from abc import ABC, abstractmethod
from datetime import date


class DashboardOperations:

    def __init__(self):
        # Replace with your data fetching logic (e.g., database connection)
        self.open_statement_count = None
        self.assigned_transaction_count = None
        self.assigned_transaction_count = None
        self.assigned_transaction_count = None
        # ... (similarly initialize other counts)

    @staticmethod
    def get_count(status=None, uploaded_status=None, assigned_user=None, start_date=None,
                  end_date=None):
        """
        Retrieves the count of BankReconciliation records based on dynamic filter parameters.

        Args:
            status (str, optional): Filter by status field. Defaults to None (no filter).
            uploaded_status (str, optional): Filter by uploaded_status field. Defaults to None (no filter).
            assigned_user (Model, optional): Filter by Assigned_User in the related banktransaction table.
                                            Defaults to None (no filter).
            start_date (datetime.date, optional): Start date for the filter on Accounting_Month. Defaults to None (no filter).
            end_date (datetime.date, optional): End date for the filter on Accounting_Month. Defaults to None (no filter).

        Returns:
            int: The count of BankReconciliation records matching the filters (or None if no records found).
        """

        filters = Q()  # Initialize an empty Q object

        # Build dynamic filters based on arguments
        # if status:
        #     filters &= Q(status=status)
        if uploaded_status:
            filters &= Q(uploaded_status__icontains=uploaded_status)
        if assigned_user:
            filters &= Q(banktransaction__Assigned_User__isnull=assigned_user)
        if start_date and end_date:
            filters &= Q(uploaded_date__range=(start_date, end_date))

        # Apply filters and count objects
        return BankReconciliation.objects.filter(filters)

    @staticmethod
    def get_banktxn_table(assigned,start_date=None,
                               end_date=None):
        filters = Q()  # Initialize an empty Q object

        # Build dynamic filters based on arguments
        if start_date and end_date:
            filters &= Q(Payment_Receive_Date__range=(start_date, end_date))
        if assigned:
            filters &= ~Q(Assigned_User=None)
        else:
            filters &= Q(Assigned_User=None)

        # Apply filters
        bank_txns = BankTransaction.objects.filter(filters, archived=False)
        return bank_txns

    @staticmethod
    def get_cashallocation_table(type,start_date=None,
                               end_date=None):
        filters = Q()  # Initialize an empty Q object

        if start_date and end_date:
            filters &= Q(bank_txn__Payment_Receive_Date__range=(start_date, end_date))
        # Build dynamic filters based on arguments
        if type == 'Unallocated':
            filters &= ~Q(allocation_status='Allocated')
        else:
            filters &= Q(allocation_status='Allocated')
        count_data = CashAllocation.objects.filter(filters, archived=False)
        return count_data if count_data else None

    @staticmethod
    def get_cash_tracker_table(status=None, start_date=None,
                               end_date=None):
        filters = Q()  # Initialize an empty Q object

        # Build dynamic filters based on arguments
        if status:
            if status=="Allocated":
                filters &= Q(Allocation_Status="Allocated")
            elif status=="Unallocated":
                filters &= ~Q(Allocation_Status="Allocated")
        if start_date and end_date:
            filters &= Q(Accounting_Monthy__range=(start_date, end_date))

        # Apply filters and count objects
        count_data = CashTracker.objects.filter(filters)
        return count_data.count() if count_data else None

    @staticmethod
    def get_open_statement_count(start_date=None, end_date=None) -> int:
        """
        Retrieves the count of open statements (assigned, uploaded, with assigned user) within a date range (optional).

        Args:
            start_date (datetime.date, optional): Start date for the query. Defaults to None (no date filter).
            end_date (datetime.date, optional): End date for the query. Defaults to None (no date filter).
            cash tracker (Model, optional): The Django model representing the cash tracker table.
                Defaults to BankReconciliation.
            cash tracker (Model, optional): The Django model representing the bank transaction table.
                Defaults to BankTransaction.

        Returns:
            int: The total count of open statements (BankReconciliation records meeting criteria).
        """

        open_statement_count = DashboardOperations.get_count(status='Assigned', uploaded_status='Uploaded',
                                                             assigned_user=False,
                                                             start_date=start_date,
                                                             end_date=end_date)

        return open_statement_count.count() if open_statement_count else None

    @staticmethod
    def get_open_statement_amount(start_date=None, end_date=None) -> int:
        open_statement_count = DashboardOperations.get_count(status='Assigned', uploaded_status='Uploaded',
                                                             assigned_user=False,
                                                             start_date=start_date,
                                                             end_date=end_date)

        return open_statement_count.aggregate(Sum('credit_amount'))

    @staticmethod
    def get_assigned_transaction_count(start_date=None, end_date=None) -> int:
        assigned_transaction_count = DashboardOperations.get_banktxn_table(assigned=True, start_date=start_date, end_date=end_date)
        return assigned_transaction_count.count()

    @staticmethod
    def get_non_assigned_transaction_count(start_date=None, end_date=None) -> int:
        unassigned_transaction_count = DashboardOperations.get_banktxn_table(assigned=False, start_date=start_date, end_date=end_date)
        return unassigned_transaction_count.count()
    
    @staticmethod
    def get_assigned_transaction_amount(start_date=None, end_date=None) -> int:
        assigned_transaction_count = DashboardOperations.get_banktxn_table(assigned=True, start_date=start_date, end_date=end_date)
        return assigned_transaction_count.aggregate(receivable_amt=Sum('Receivable_Amount'))
    
    @staticmethod
    def get_non_assigned_transaction_amount(start_date=None, end_date=None) -> int:
        assigned_transaction_count = DashboardOperations.get_banktxn_table(assigned=False, start_date=start_date, end_date=end_date)
        return assigned_transaction_count.aggregate(receivable_amt=Sum('Receivable_Amount'))

    @staticmethod
    def get_allocated_transaction_count(start_date=None, end_date=None) -> int:
        cashallocation_data = DashboardOperations.get_cashallocation_table(type='Allocated', start_date=start_date,end_date=end_date)
        return cashallocation_data.count() if cashallocation_data else 0

    @staticmethod
    def get_unallocated_transaction_count(start_date=None, end_date=None) -> int:
        cashallocation_data = DashboardOperations.get_cashallocation_table(type='Unallocated', start_date=start_date,end_date=end_date)
        return cashallocation_data.count() if cashallocation_data else 0
    
    @staticmethod
    def get_unallocated_transaction_amount(start_date=None, end_date=None) -> int:
        cashallocation_data = DashboardOperations.get_cashallocation_table(type='Unallocated', start_date=start_date,end_date=end_date)
        return cashallocation_data.aggregate(receivable_amt=Sum('receivable_amt')) if cashallocation_data else 0
    
    @staticmethod
    def get_allocated_transaction_amount(start_date=None, end_date=None) -> int:
        cashallocation_data = DashboardOperations.get_cashallocation_table(type='allocated', start_date=start_date,end_date=end_date)
        return cashallocation_data.aggregate(receivable_amt=Sum('receivable_amt')) if cashallocation_data else 0
    
    
    @staticmethod
    def get_user_count(start_date=None, end_date=None):
        assigned_user_count=BankTransaction.objects.filter(Q(assigned_date__range=[start_date, end_date]), ~Q(Assigned_User_id=None), archived=False).count()
        completed_user_count=CashAllocation.objects.filter(allocation_date__range=[start_date, end_date], allocation_status="Allocated", archived=False).count()

        return {'assigned_user_count':assigned_user_count, 'completed_user_count':completed_user_count }
    
    @staticmethod
    def get_datewise_total_amount(start_date=None, end_date=None ): 
        datewise_receivable_amount=CashTracker.objects.filter(Payment_Receive_Date__range=[start_date, end_date]).values("Payment_Receive_Date").annotate(total_receivable_amt=Sum("Receivable_Amount")).order_by("Payment_Receive_Date")
        datewise_allocated_amount= CashAllocation.objects.filter(allocation_date__range=[start_date, end_date], allocation_status="Allocated", archived=False).values("allocation_date").annotate(total_allocated_amt=Sum("allocated_amt")).order_by("allocation_date")
        
        return {"datewise_receivable_amount":datewise_receivable_amount, "datewise_allocated_amount":datewise_allocated_amount}

    @staticmethod
    def get_total_amount(start_date=None, end_date=None):
        total_allocated_amt=CashAllocation.objects.filter(Q(allocation_date__range=[start_date, end_date]),Q(allocation_status="Allocated"),archived=False).aggregate(allocated_amt_total=Sum("allocated_amt"))
        total_receivable_amt=CashTracker.objects.filter(Payment_Receive_Date__range=[start_date, end_date]).aggregate(receivable_amt_total=Sum("Receivable_Amount"))
        unallocated_statuswise_amt=CashAllocation.objects.exclude(allocation_status="Allocated", archived=False).values("allocation_status").annotate(total_category_wise_amt=Sum("unallocated_amt", filter=Q(cashtrackerreport__Payment_Receive_Date__range=[start_date, end_date])))                                                                                                         
        total_unallocated_amt=CashAllocation.objects.filter(cashtrackerreport__Payment_Receive_Date__range=[start_date, end_date], archived=False).aggregate(total_unallocated_amt=Sum("unallocated_amt"))
        
        return {'total_receivable_amt':total_receivable_amt,'total_allocated_amt':total_allocated_amt,'total_unallocated_amt':total_unallocated_amt, 'unallocated_statuswise_amt': unallocated_statuswise_amt  }

    @staticmethod
    def sla(start_date=None, end_date=None):
        sla_met=CashTrackerReport.objects.filter(SLA_Compliance="Met", bank_txn_id__created_at__range=[start_date, end_date]).count()
        sla_not_met=CashTrackerReport.objects.filter(~Q(SLA_Compliance="Met"), bank_txn_id__created_at__range=[start_date, end_date]).count()
        return {"sla_met": sla_met, "sla_not_met": sla_not_met}

    @staticmethod
    def employee_allocation_data(start_date=None, end_date=None):
        employee_data=BankTransaction.objects.filter(archived=False, assigned_date__range=[start_date, end_date]).values("Assigned_User_id__user_name").annotate(employee_receivable_count=Count('cashallocation'), employee_allocated_count=Count('cashallocation', filter=Q(cashallocation__allocation_status="Allocated", cashallocation__allocation_date__range=[start_date, end_date])) ).annotate(user_name= F("Assigned_User_id__user_name"))     
        
        return employee_data
    
    @staticmethod
    def get_allocation_status_count(start_date=None, end_date=None):
        allocation_status_count=CashAllocation.objects.filter(archived=False, allocation_status="Allocated", allocation_date__range=[start_date, end_date]).count()
        unallocation_statuswise_count=CashAllocation.objects.filter(archived=False, cashtrackerreport__Payment_Receive_Date__range=[start_date, end_date]).values('allocation_status').annotate(
            unallocation_status_count=Count('id'), 
            unallocated_amt=Sum('unallocated_amt', filter=~Q(allocation_status="Allocated"))
        ).filter(~Q(allocation_status="Allocated"))
        total_unallocated_count=CashAllocation.objects.filter(~Q(allocation_status="Allocated"), Q(cashtrackerreport__Payment_Receive_Date__range=[start_date, end_date]), archived=False).count()
        total_count=CashAllocation.objects.filter(cashtrackerreport__Payment_Receive_Date__range=[start_date, end_date], archived=False).count()
       
        return {'allocation_status_count':allocation_status_count, 'unallocation_statuswise_count':unallocation_statuswise_count, 'total_unallocated_count':total_unallocated_count, 'total_count':total_count}
    
    @staticmethod
    def get_credit_debit_amount(start_date=None, end_date=None):
        credit_debit_total_amount=BankTransaction.objects.filter(archived=False, Payment_Receive_Date__range=[start_date, end_date]).select_related("bank_reconciliation").values("Payment_Receive_Date", "Receiving_Bank_Account").annotate(credit_total_amount=Sum("bank_reconciliation__credit_amount"), debit_total_amount=Sum("bank_reconciliation__debit_amount"))
        return credit_debit_total_amount
    
    @staticmethod
    def get_allocated_data_amount(start_date=None, end_date=None):
        allocated_data_amount=CashAllocation.objects.filter(archived=False, allocation_date__range=[start_date, end_date]).values("allocation_date").annotate(credit_total_amount=Sum("receivable_amt"), debit_total_amount=Sum("allocated_amt"))
        
        return allocated_data_amount
    
    @staticmethod
    def get_target_goals(start_date=None, end_date=None):
        target_goals=CashAllocation.objects.filter(archived=False, allocation_date__range=[start_date, end_date]).aggregate(Sum("receivable_amt"), Sum("allocated_amt"))
        target_goals['receivable_amt_sum'] = target_goals['receivable_amt__sum']
        target_goals['allocated_amt_sum'] = target_goals['allocated_amt__sum']
        target_goals.pop('receivable_amt__sum')
        target_goals.pop('allocated_amt__sum')
        return target_goals

    @staticmethod
    def get_employee_wise_status_info(start_date=None, end_date=None):
        employee_status_wise_count=BankTransaction.objects.filter(archived=False, assigned_date__range=[start_date, end_date]).values("Assigned_User_id__user_name" , "cashallocation__allocation_status").annotate(status_count=Count("cashallocation__id")).annotate(user_name= F("Assigned_User_id__user_name"), allocation_status=F("cashallocation__allocation_status"))
        return employee_status_wise_count
