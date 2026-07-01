from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register("document_upload", views.DocumentsViewSet, basename='document_upload')
router.register("policy_create", views.PolicyCreateViewSet, basename='policy_create')
router.register("lob", views.LOBViewSet, basename='lob')
router.register("scm_partners", views.SCMPartnersViewSet, basename='scm_partners')
router.register("binding_agreement", views.BindingAgreementViewSet, basename='binding_agreement')
router.register("cash_transfer", views.CashTransferViewSet, basename='cash_transfer')
router.register("entity", views.EntityViewSet, basename='entity')
router.register("policydata", views.PolicyViewSet, basename='policydata')
router.register("issue_catergory", views.IssueCatergoryViewSet, basename='issue_catergory')
router.register("exchange_rate", views.BankExchangeRateViewSet, basename='exchange_rate')
router.register("policy_line_ref", views.PolicyInformationViewSet, basename='policy_line_ref')
router.register("escalation", views.EscalationViewSet, basename='escalation')
router.register("roe_file_upload", views.ROEFileUploadViewSet, basename='roe_file_upload')
router.register("sla", views.SLAViewSet, basename='sla')
router.register("participating_insurer", views.ParticipatingInsurerViewSet, basename='participating_insurer')
router.register("sirius_data", views.SiriusDataViewSet, basename='sirius_data')
router.register("rbs_details", views.RBSDetailsViewSet, basename='rbs_details')
router.register("mop_mapping", views.MOPMappingViewSet, basename='mop_mapping')
router.register("aon_ledger", views.AONLedgerViewSet, basename='aon_ledger')
router.register("roe_file_upload", views.ROEFileUploadViewSet, basename='roe_file_upload')
router.register("aged_debt_due", views.AgedDebtDueViewSet, basename='aged_debt_due')
router.register("aged_debt_due_management", views.AgedDebtDueManagementViewSet, basename='aged_debt_due_management')
router.register("chaser_indicator", views.ChaserIndicatorViewSet, basename='chaser_indicator')

urlpatterns = [
    path('',include(router.urls)),
    path('broker_excel_import/', views.broker_excel_import, name='broker_excel_import'),
    path('currency_excel_import/', views.currency_excel_import, name='currency_excel_import'),
    path('bank_excel_upload/', views.BankDetailsAPIView.as_view(), name='bank_excel_upload'),
    path('get_banks_list/', views.getAllBankNames, name='get_banks_list'),
    path('get_all_unique_bank_names/', views.get_all_unique_bank_names, name='get_all_unique_bank_names'),
    path('get_all_unique_account_numbers_by_bank_name/', views.get_all_unique_account_numbers_by_bank_name, name='get_all_unique_account_numbers_by_bank_name'),
    path('get_details_by_bank/', views.getDetailsByBankName, name='get_details_by_bank'),
    path('get_bank_details_for_filters/', views.getBankDetailsForFilter, name='get_bank_details_for_filters'),
    path('get_policy_details_by_policy_ref/', views.getDetailsByPolicyRef, name='get_policy_details_by_policy_ref'),
    path('get_broker_list/', views.getAllBrokerList, name='get_broker_list'),
    path('get_broker_by_broker_name/', views.BrokerNameInfoViewSet.as_view(), name='get_broker_by_broker_name'),
    path('get_broker_by_broker_branch_name/', views.BrokerBranchNameInfoViewSet.as_view(), name='get_broker_by_broker_branch_name'),
    path('policy_data_excel_import/', views.policy_data_excel_import, name='policy_data_excel_import'),
    path('exchange_rate_excel_import/', views.exchange_rate_excel_import, name='exchange_rate_excel_import'),
    path('get_broker_by_broker_branch_namee/', views.getDetailsByBrokerBranchName, name='get_broker_by_broker_branch_namee'),
    path('bank_data/', views.BankInfoViewSet.as_view(), name='bank_data'),
    path('bank_data/<pk>/', views.BankInfoViewSet.as_view(), name='bank_data_update'),
    path("policy_type/", views.PolicyTypeViewSet.as_view(), name='policy_type'),
    path("policy_type/<pk>/", views.PolicyTypeViewSet.as_view(), name='policy_type_update'),

    path("currency_details/", views.CurrencyViewSet.as_view(), name='currency_details'),
    path("currency_details/<pk>/", views.CurrencyViewSet.as_view(), name='currency_details_update'),

    path("allocation_status/", views.AllocationStatusViewSet.as_view(), name='allocation_status'),
    path("allocation_status/<pk>/", views.AllocationStatusViewSet.as_view(), name='allocation_status_update'),

    path("correction_type/", views.CorrectionTypeViewSet.as_view(), name='correction_type'),
    path("correction_type/<pk>/", views.CorrectionTypeViewSet.as_view(), name='correction_type_update'),
   
    path("transaction_category/", views.TransactionCategoryViewSet.as_view(), name='transaction_category'),
    path("transaction_category/<pk>/", views.TransactionCategoryViewSet.as_view(), name='transaction_category_update'),

    path("broker_info/", views.BrokerInfoViewSet.as_view(), name='broker_info'),
    path("broker_info/<pk>/", views.BrokerInfoViewSet.as_view(), name='broker_info_update'),
    path("powerbi_reports/", views.PowerBIReportViewSet.as_view({'get': 'list'}), name='powerbi_reports'),
    path("decrypt_data/", views.DecryptDataAPIView.as_view(), name='decrypt_data'),

    path('get_all_currencies/', views.get_all_currencies, name='get_all_currencies'),
    path('get_all_entity_divisions/', views.get_all_entity_divisions, name='get_all_entity_divisions'),

    path("txn_status/", views.TxnStatusViewset.as_view(), name='txn_status'),
    path("txn_status/<pk>/", views.TxnStatusViewset.as_view(), name='txn_status_update'),

    path("aged_report_data/", views.FileRecordViewSet.as_view({'get': 'list'}), name='aged_report_data'),
    path('policy_data/', views.policy_data_json, name='policy_data_json'),
    path('download_policy_data/', views.policy_data_excel, name='policy_data_excel'),
    path('run_age_dept_report/', views.TriggerPolicyCalculationView.as_view(), name='trigger-policy-calculation'),
    path('get_aged_dept_years/', views.get_aged_dept_years, name='get_aged_dept_years'),
    path('get_calulation_files_list/', views.get_calulation_files_list, name='get_calulation_files_list'),
    path('get_agedept_details/', views.get_agedept_details, name='get_agedept_details'),

    path('lob_filter/', views.LOBFilterViewSet, name='lob_filter'),
    path('yoa_filter/', views.YOAPolicyFilterViewSet, name='yoa_filter'),
    path('aged_debt_action_filter/', views.agedDebtActionFilter, name='aged_debt_action_filter'),
    path('aged_debt_category_filter/', views.agedDebtCategoryFilter, name='aged_debt_category_filter'),
    path('get_bank_details_list/', views.getBankDetailsList, name='get_bank_details_list'),
    path('download_allocation_status/', views.downloadAllocationStatus, name='download_allocation_status'),
    path('download_exchange_rate/', views.downloadExchangeRate, name='download_exchange_rate'),
    path('download_bank_info/', views.downloadBankInfo, name='download_bank_info'),
    path('download_binding_agreement/', views.downloadBindingAgreement, name='download_binding_agreement'),
    path('download_broker_info/', views.downloadBrokerInfo, name='download_broker_info'),
    path('download_correction_type/', views.downloadCorrectionType, name='download_correction_type'),
    path('download_corrective_transfer/', views.downloadCorrectiveTransfer, name='download_corrective_transfer'),
    path('download_currency_details/', views.downloadCurrency, name='download_currency_details'),
    path('download_entity/', views.downloadEntity, name='download_entity'),
    path('download_lob/', views.downloadLOB, name='download_lob'),
    path('download_policy_type/', views.downloadPolicyType, name='download_policy_type'),
    path('download_scm_partners/', views.downloadSCMPartners, name='download_scm_partners'),
    path('download_participating_insurer/', views.downloadParticipatingInsurer, name='download_participating_insurer'),
    path('download_escalation/', views.downloadEscalation, name='download_escalation'),
    path('download_transaction_category/', views.downloadTransactionCategory, name='download_transaction_category'),
    path('download_txn_status/', views.downloadTransactionStatus, name='download_txn_status'),
    path("agedebt_action/", views.AgedDebtActionViewSet.as_view(), name='agedebt_action'),
    path("agedebt_action/<pk>/", views.AgedDebtActionViewSet.as_view(), name='agedebt_action_update'),
    path("agedebt_category/", views.AgedDebtCategoryViewSet.as_view(), name='agedebt_category'),
    path("agedebt_category/<pk>/", views.AgedDebtCategoryViewSet.as_view(), name='agedebt_category_update'),
]