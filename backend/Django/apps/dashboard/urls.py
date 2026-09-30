"""
URL configuration for Dashboard module.
"""
from django.urls import path
from .views import (
    dashboard_overview_view,
    dashboard_water_level_trend_view,
    dashboard_alert_history_view,
    dashboard_sms_statistics_view,
    dashboard_prediction_accuracy_view,
    dashboard_resident_distribution_view,
    dashboard_system_status_view,
    dashboard_telemetry_view,
    dashboard_decision_support_view,
    dashboard_water_level_forecast_view,
    dashboard_monthly_water_level_forecast_view,
)

urlpatterns = [
    path('overview/', dashboard_overview_view, name='dashboard_overview'),
    path('water-level-trend/', dashboard_water_level_trend_view, name='water_level_trend'),
    path('alert-history/', dashboard_alert_history_view, name='alert_history'),
    path('sms-statistics/', dashboard_sms_statistics_view, name='sms_statistics'),
    path('prediction-accuracy/', dashboard_prediction_accuracy_view, name='prediction_accuracy'),
    path('resident-distribution/', dashboard_resident_distribution_view, name='resident_distribution'),
    path('system-status/', dashboard_system_status_view, name='system_status'),
    path('telemetry/', dashboard_telemetry_view, name='telemetry'),
    path('decision-support/', dashboard_decision_support_view, name='decision_support'),
    path('water-level-forecast/', dashboard_water_level_forecast_view, name='water_level_forecast'),
    path('monthly-water-level-forecast/', dashboard_monthly_water_level_forecast_view, name='monthly_water_level_forecast'),
]
