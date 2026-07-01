from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

urlpatterns = [
    path('premium_bdx_report/', views.PremiumBDXReport.as_view(), name='premium_bdx_report'),
    path('premium_bdx_file/', views.PremBDXFileViewSet.as_view({'get': 'list'}), name='premium_bdx_file'),
    path('read-data/', views.read_data, name='read_data'),
    path('payment_treasury/',
         views.PaymentTreasuryPYMTViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'update'}),
         name='payment_treasury'),
    path('payment_treasury/<pk>/', views.PaymentTreasuryPYMTViewSet.as_view({'patch': 'update'}),
         name='update_payment_treasury'),
    path('payment_file/', views.PaymentFileViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'update'}),
         name='payment_file'),
    path('payment_file/<pk>/', views.PaymentFileViewSet.as_view({'patch': 'update'}),
         name='update_payment_file'),
    path('get_all_paymentid', views.GetAllPaymentId.as_view(),
         name='get_all_paymentid'),

     path('exception_file/',
         views.ExceptionFileAPIView.as_view()),
    path('exception_file/<int:pk>/',
         views.ExceptionFileAPIView.as_view()),
    path('payment_overall_status/overall_status/', views.PaymentFileOverallStatusViewSet.as_view({'get': 'list'}), name="payment-file-overall-status"),

     path('initiate_wf_exception/',
         views.InitiateWFException.as_view()),

     path('payment_datasheet/', views.PaymentDatasheetViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='payment_datasheet'),
    path('payout_summary/', views.PayoutSummaryViewSet.as_view(), name='payout_summary'),
    path('payout_summary/<int:pk>/', views.PayoutSummaryViewSet.as_view(), name='payout_summary_edit'),
    path('payout_summary_payment_id/', views.PayoutSummaryIDViewSet.as_view(), name='payout_summary_id'),
    path('coversheet/', views.CoversheetViewSet.as_view({'get': 'list'}), name='coversheet'),
]
