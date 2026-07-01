from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()

router.register("bank_transaction", views.BankTransactionViewSet, basename='bank_transaction')
router.register("user_assigned_for_transaction", views.UserAssignedForTransactionViewSet,
                basename='user_assigned_for_transaction')
router.register("user_assign_transactions", views.UserAssignTransactionsViewSet, basename='user_assign_transactions')
router.register("multiple_assign_transactions_to_user", views.MultiAssignTransactionsToUserViewSet,
                basename='multiple_assign_transactions_to_user')
router.register("cash_allocation", views.CashAllocationViewSet, basename='cash_allocation')
router.register("file_upload_to_transactions", views.FileUploadToTransactionsViewSet,
                basename='file_upload_to_transactions')
router.register("multi_file_upload_to_transactions", views.MultiFileUploadToTransactionsViewSet,
                basename='multi_file_upload_to_transactions')
router.register("cash_allocation_issues", views.CashAllocationIssuesViewSet, basename='cash_allocation_issues')
router.register("cash_allocation_corrective", views.CashAllocationCorrectiveViewSet,
                basename='cash_allocation_corrective')
router.register("cash_allocation_writeoff", views.CashAllocationWriteoffViewSet, basename='cash_allocation_writeoff')
router.register("cash_allocation_refund", views.CashAllocationRefundViewSet, basename='cash_allocation_refund')
router.register("cash_allocation_cfi", views.CashAllocationCFIViewSet, basename='cash_allocation_cfi')
router.register("cross_allocation", views.CrossAllocationViewSet, basename='cross_allocation')
router.register("cash_allocation_msd", views.CashAllocationMSDViewSet, basename='cash_allocation_msd')
router.register("premium_payment", views.PremiumPaymentViewSet, basename='premium_payment')
router.register("corrective_trf", views.CorrectiveTRFViewSet, basename='corrective_trf')
router.register("workstep", views.WorkStepViewSet, basename='workstep')
router.register("workflow", views.WorkFlowViewSet, basename='workflow')
router.register("cash_tracker", views.CashTrackerViewSet, basename='cash_tracker')
router.register("cash_tracker_report", views.CashTrackerReportViewSet, basename='cash_tracker_report')
router.register("workflow_bank_transactions", views.WorkflowBankTransactionsViewSet,
                basename='workflow_bank_transactions')
router.register("bank_reconciliation", views.BankReconciliationViewSet, basename='bank_reconciliation')
router.register("bank_reconciliation_accountno", views.BankReconciliationAccountNoViewSet,
                basename='bank_reconciliation_accountno')
router.register("accounting_month_end", views.AccountingMonthEndViewSet, basename='accounting_month_end')
router.register("chaser", views.ChaserViewset, basename='chaser')

urlpatterns = [
    path('', include(router.urls)),
    path('get_bankdetails_by_txn_id/', views.getBankDetailsByTransactionId, name='get_bankdetails_by_txn_id'),
    path('get_transactions_by_txn_id/', views.GetTransactionsByTransactionId.as_view(),
         name='get_transactions_by_txn_id'),
    path('get_transactions_by_txn_id_validation/', views.GetTransactionsByTransactionIdValidation.as_view(),
         name='get_transactions_by_txn_id_validation'),
    path('get_issues_by_allocation_id/', views.getCashAllocationIssuesFromCashAllocation,
         name='get_issues_by_allocation_id'),
    path('get_corrective_by_allocation_id/', views.getCashAllocationCorrectiveFromCashAllocation,
         name='get_corrective_by_allocation_id'),
    path('get_writeoff_by_allocation_id/', views.getCashAllocationWriteoffFromCashAllocation,
         name='get_writeoff_by_allocation_id'),
    path('get_refund_by_allocation_id/', views.getCashAllocationRefundFromCashAllocation,
         name='get_refund_by_allocation_id'),
    path('get_cfi_by_allocation_id/', views.getCashAllocationCFIFromCashAllocation, name='get_cfi_by_allocation_id'),
    path('get_cross_allocation_by_allocation_id/', views.getCrossAllocationFromCashAllocation,
         name='get_cross_allocation_by_allocation_id'),
    path('get_msd_by_allocation_id/', views.getCashAllocationMSDFromCashAllocation, name='get_msd_by_allocation_id'),
    path('get_premium_payment_by_allocation_id/', views.getPremiumPaymentFromCashAllocation,
         name='get_premium_payment_by_allocation_id'),
    path('get_corrective_trf_by_allocation_id/', views.getCorrectiveTRFFromCashAllocation,
         name='get_corrective_trf_by_allocation_id'),
    path('workflow_assign_transaction/', views.setWorkflowWithTransaction, name='workflow_assign_transaction'),
    path('cash_tracker_excel_import/', views.cash_tracker_excel_import, name='cash_tracker_excel_import'),
    path('get_cash_tracker/', views.getCashTracker, name='get_cash_tracker'),
    path('bank_transaction_filter_with_search/', views.BankTransactionSearchViewSet.as_view(),
         name="bank_transaction_filter_with_search"),
    path('get_workflow_list_id/', views.getWorkflowList, name='get_workflow_list_id'),
    path('bank_transactions_search/', views.BankTransactionList.as_view(), name='bank-transaction-list'),
    path('bank_transaction/', views.BankTransactionGetList.as_view(), name='bank-transaction'),
    path('cash_allocation_search/', views.CashAllocationList.as_view(), name='cash-allocation-list'),
    path('cash_tracker_search/', views.CashTrackerList.as_view(), name='cash-tracker-list'),
    path('bank_transaction_workflow_status_check/', views.BankTransactionWorkflowStatusViewSet.as_view(),
         name="bank_transaction_workflow_status_check"),
    path('export_cash_tracker_report/', views.getCashTrackerExport, name='cash-tracker-export'),
    path('upload_bank_files/', views.UploadFileView.as_view(), name="upload_file"),
    path('dashboard/', views.BankmanagementDashboard.as_view(), name="dashboard"),
    path('dashboard_bank_balance/', views.BankBalanceDashboard.as_view(), name="dashboard-bank-balance"),
    path('get_bank_names/', views.BankNames.as_view(), name="bank_name"),
    path('get_bank_account_based_on_bank_name/', views.BankAccountBasedOnBankName.as_view(), name="bank_account_based_on_bank_name"),
    path('cash_allocation_locked_unlocked/', views.CashAllocationAllocatedTransaction.as_view(),
         name="cash_allocation_locked_unlocked"),
    path('cash_allocation_locked_unlocked_history/', views.CashAllocationLockedUnlockedHistoryList.as_view(),
         name="cash_allocation_locked_unlocked_history"),
    path("cash_tracker_report_based_on_cash_allocation/", views.CashTrackerReportForCashAllocation.as_view(), name='cash_tracker_report_based_on_cash_allocation'),
    path("cash_allocation_activities/<str:id>/", views.CheckCashAllocationActivities.as_view(), name='cash_allocation_activities'),
    path("cash_allocation_update/<str:pk>/", views.CashAllocationUpdateAPIView.as_view(), name='cash_allocation_update'),
    path("workstep_user_update/<str:pk>/", views.WorkstepUserUpdateAPIView.as_view(), name="workstep_user_update"),
    path('download/', views.DownloadFileView.as_view(), name='download-file'),
    path('download_accounting_month_end/', views.downloadAccountingMonthEnd, name='download_accounting_month_end'),
    path('assign_policy_handler/', views.AssignPolicyHandler.as_view(), name='assign_policy_handler')
]