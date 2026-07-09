from django.urls import path
from . import views

urlpatterns = [
    path('', views.BatteryListView.as_view(), name='battery_list'),
    path('batteries/', views.BatteryListView.as_view(), name='battery_list'),
    path('batteries/<int:pk>/', views.BatteryDetailView.as_view(), name='battery_detail'),    
    path('batteries/<int:pk>/quick-charge/', views.BatteryQuickChargeView.as_view(), name='battery_quick_charge'),
    path('batteries/<int:pk>/qr/', views.battery_qr_code, name='battery_qr_code'),
    path('batteries/<int:pk>/label/', views.battery_label_pdf, name='battery_label_pdf'),
    path('events/', views.ChargeEventListView.as_view(), name='charge_event_list'),
    path('events/new/', views.ChargeEventCreateView.as_view(), name='charge_event_create'),
    path('events/<int:pk>/edit/', views.ChargeEventUpdateView.as_view(), name='charge_event_update'),
    path('charts/voltages/', views.VoltageChartView.as_view(), name='voltage_chart'),
    path('api/batteries/<int:pk>/', views.battery_api, name='battery_api'),
]
