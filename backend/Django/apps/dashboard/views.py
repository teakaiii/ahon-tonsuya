"""
Views for Dashboard module - provides aggregated data for the frontend dashboard.
"""
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
from django.db import models


def _threshold_band(status_value):
    if status_value == 'Danger':
        return 'critical'
    if status_value in {'Alert', 'Warning'}:
        return 'warning'
    if status_value in {'No Data', 'Out of Range'}:
        return 'unknown'
    return 'normal'


def _telemetry_status(reading):
    from apps.water_level.models import WaterLevelReading

    status = WaterLevelReading.get_flood_status(reading.water_level_cm)
    band = _threshold_band(status)
    alert_level = {
        'normal': 'Normal',
        'warning': 'Warning',
        'critical': 'Critical',
    }.get(band, 'Normal')
    return status, band, alert_level


def _decision_support(reading, previous_reading=None, force_stale=False):
    if not reading:
        return {
            'status_summary': 'No valid water-level telemetry is available.',
            'status': 'No Data',
            'band': 'unknown',
            'risk_percentage': 0,
            'data_confidence': 0,
            'risk_metric_label': 'Operational risk score, not a statistical probability.',
            'trend_change': None,
            'trend_change_percentage': None,
            'key_findings': ['No calibrated sensor reading is available.'],
            'recommended_actions': ['Check the sensor connection and calibration.'],
            'basis': 'No valid water-level telemetry is available.',
            'is_stale': True,
            'reading_age_seconds': None,
        }

    from apps.water_level.models import WaterLevelReading

    status_value = WaterLevelReading.get_flood_status(reading.water_level_cm)
    level = float(reading.water_level_cm)
    reading_age = max(0, int((timezone.now() - reading.timestamp).total_seconds()))
    is_stale = force_stale or reading_age > settings.READING_STALE_AFTER_SECONDS
    change = None
    change_percentage = None
    if reading and previous_reading:
        change = round(level - float(previous_reading.water_level_cm), 2)
        previous_level = float(previous_reading.water_level_cm)
        if previous_level:
            change_percentage = round((change / previous_level) * 100, 1)

    risk_score_by_status = {
        'Normal': 10,
        'Alert': 40,
        'Warning': 65,
        'Danger': 90,
    }
    risk_percentage = risk_score_by_status.get(status_value, 0)
    if change is not None:
        if change > 0:
            risk_percentage += 5
        elif change < 0:
            risk_percentage -= 5
    risk_percentage = max(0, min(100, risk_percentage))
    data_confidence = 0 if is_stale else 100 if reading.sensor_status == 'online' else 50
    if not is_stale and reading.gsm_status != 'connected':
        data_confidence -= 20

    if status_value == 'Danger':
        summary = 'Critical water level recorded.'
        findings = [
            f'Latest reading: {level:.2f} cm.',
            'The recorded status is Danger.',
        ]
        actions = [
            'Activate the barangay emergency response protocol.',
            'Verify the reading with a second measurement or field check.',
            'Prepare resident warning or evacuation messaging.',
        ]
    elif status_value in {'Alert', 'Warning'}:
        summary = 'Water level requires active monitoring.'
        findings = [
            f'Latest reading: {level:.2f} cm.',
            f'The recorded status is {status_value}.',
        ]
        actions = [
            'Increase monitoring frequency and verify sensor health.',
            'Review the latest telemetry trend for continued increase.',
            'Prepare an advisory if the next readings remain elevated.',
        ]
    else:
        summary = 'Water level is within the recorded normal range.'
        findings = [
            f'Latest reading: {level:.2f} cm.',
            'No warning or critical threshold breach is recorded.',
        ]
        actions = ['Continue routine telemetry monitoring.']

    if change is not None:
        direction = 'increased' if change > 0 else 'decreased' if change < 0 else 'is unchanged'
        if change_percentage is None:
            findings.append(f'The recorded level {direction} by {abs(change):.2f} cm from the previous reading.')
        else:
            findings.append(
                f'The recorded level {direction} by {abs(change):.2f} cm '
                f'({abs(change_percentage):.1f}%) from the previous reading.'
            )

    if is_stale:
        summary = f'Latest valid sensor reading is stale. {summary}'
        findings.append('Verify the sensor connection; this value may no longer be current.')
        actions.insert(0, 'Verify the sensor and obtain a fresh calibrated reading.')

    at_calibrated_limit = level >= settings.SENSOR_MAX_LEVEL_CM
    if at_calibrated_limit:
        findings.append(
            f'The reading is at the calibrated {settings.SENSOR_MAX_LEVEL_CM:g} cm limit; actual level may be higher.'
        )
        actions.insert(0, 'Verify the water level with a wider-range measurement.')

    return {
        'status_summary': summary,
        'status': status_value,
        'band': _threshold_band(status_value),
        'risk_percentage': risk_percentage,
        'data_confidence': data_confidence,
        'risk_metric_label': 'Operational risk score, not a statistical probability.',
        'trend_change': change,
        'trend_change_percentage': change_percentage,
        'key_findings': findings,
        'recommended_actions': actions,
        'basis': 'Recorded water-level telemetry and status values only.',
        'is_stale': is_stale,
        'reading_age_seconds': reading_age,
        'at_calibrated_limit': at_calibrated_limit,
    }


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_telemetry_view(request):
    """Return the newest telemetry rows for the administrator history table."""
    from apps.water_level.models import WaterLevelReading

    limit = min(max(int(request.query_params.get('limit', 25)), 1), 100)
    readings = WaterLevelReading.objects.filter(
        water_level_cm__gte=0,
        water_level_cm__lte=settings.SENSOR_MAX_LEVEL_CM,
        sensor_status='online',
    ).order_by('-timestamp')[:limit]
    return Response([
        {
            'reading_id': str(reading.reading_id),
            'timestamp': reading.timestamp.isoformat(),
            'water_level_cm': float(reading.water_level_cm),
            'status': (status := _telemetry_status(reading))[0],
            'band': status[1],
            'alert_level': status[2],
            'within_calibrated_range': True,
            'sensor_status': reading.sensor_status,
            'gsm_status': reading.gsm_status,
        }
        for reading in readings
    ])


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_decision_support_view(request):
    """Return deterministic admin guidance derived from the latest readings."""
    from apps.water_level.models import WaterLevelReading

    latest_report = WaterLevelReading.objects.order_by('-timestamp').first()
    readings = list(WaterLevelReading.objects.filter(
        water_level_cm__gte=0,
        water_level_cm__lte=settings.SENSOR_MAX_LEVEL_CM,
        sensor_status='online',
    ).order_by('-timestamp')[:2])
    latest = readings[0] if readings else None
    previous = readings[1] if len(readings) > 1 else None
    invalid_report_is_newer = bool(
        latest_report
        and (
            not 0 <= latest_report.water_level_cm <= settings.SENSOR_MAX_LEVEL_CM
            or latest_report.sensor_status != 'online'
        )
        and (not latest or latest_report.timestamp > latest.timestamp)
    )
    response = _decision_support(latest, previous, force_stale=invalid_report_is_newer)
    if invalid_report_is_newer:
        response['key_findings'].append(
            f'Latest reported value is outside the calibrated 0-{settings.SENSOR_MAX_LEVEL_CM:g} cm range.'
        )
    response['timestamp'] = latest.timestamp.isoformat() if latest else None
    response['reading_id'] = str(latest.reading_id) if latest else None
    return Response(response)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_water_level_forecast_view(request):
    """Return a real-data regression forecast and chronological holdout metrics."""
    from apps.water_level.models import WaterLevelReading
    from .forecasting import forecast_water_level

    readings = WaterLevelReading.objects.filter(
        water_level_cm__gte=0,
        water_level_cm__lte=settings.SENSOR_MAX_LEVEL_CM,
        sensor_status='online',
    ).order_by('timestamp').values_list(
        'timestamp', 'water_level_cm'
    )
    return Response(forecast_water_level(readings))


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_monthly_water_level_forecast_view(request):
    """Return a same-month daily baseline using prior years' stored readings."""
    from apps.water_level.models import WaterLevelReading
    from .forecasting import forecast_month_profile

    try:
        year = int(request.query_params.get('year', ''))
        month = int(request.query_params.get('month', ''))
    except (TypeError, ValueError):
        return Response({'detail': 'Valid year and month parameters are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if not 2000 <= year <= 2100 or not 1 <= month <= 12:
        return Response({'detail': 'Year must be 2000-2100 and month must be 1-12.'}, status=status.HTTP_400_BAD_REQUEST)

    forecast_start = timezone.make_aware(
        datetime(year, month, 1),
        timezone.get_current_timezone(),
    )
    readings = WaterLevelReading.objects.filter(
        timestamp__lt=forecast_start,
        water_level_cm__gte=0,
        water_level_cm__lte=settings.SENSOR_MAX_LEVEL_CM,
        sensor_status='online',
    ).order_by('timestamp').values_list('timestamp', 'water_level_cm')
    return Response(forecast_month_profile(readings, year, month))


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_overview_view(request):
    """
    API endpoint to get dashboard overview data.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.water_level.models import WaterLevelReading
    from apps.alerts.models import FloodAlert
    from apps.residents.models import Resident
    from apps.sms.models import SMSLog
    from apps.predictions.models import Prediction
    
    latest_report = WaterLevelReading.objects.order_by('-timestamp').first()
    current_reading = WaterLevelReading.objects.filter(
        water_level_cm__gte=0,
        water_level_cm__lte=settings.SENSOR_MAX_LEVEL_CM,
        sensor_status='online',
    ).order_by('-timestamp').first()
    invalid_report_is_newer = bool(
        latest_report
        and (
            not 0 <= latest_report.water_level_cm <= settings.SENSOR_MAX_LEVEL_CM
            or latest_report.sensor_status != 'online'
        )
        and (not current_reading or latest_report.timestamp > current_reading.timestamp)
    )
    age_reference = current_reading or latest_report
    reading_age = (
        max(0, int((timezone.now() - age_reference.timestamp).total_seconds()))
        if age_reference else None
    )
    reading_is_stale = (
        not current_reading
        or reading_age > settings.READING_STALE_AFTER_SECONDS
        or invalid_report_is_newer
        or current_reading.sensor_status != 'online'
    )
    data_quality_issue = None
    if invalid_report_is_newer:
        data_quality_issue = (
            f'Latest sensor report is outside the calibrated 0-{settings.SENSOR_MAX_LEVEL_CM:g} cm range or is marked faulty.'
        )
    elif current_reading and current_reading.water_level_cm >= settings.SENSOR_MAX_LEVEL_CM:
        data_quality_issue = (
            f'Reading is at the calibrated {settings.SENSOR_MAX_LEVEL_CM:g} cm limit; actual level may be higher.'
        )
    
    # Active alerts
    active_alerts = FloodAlert.objects.filter(is_active=True).count()
    
    # Resident statistics
    total_residents = Resident.objects.count()
    if total_residents == 0:
        # Create sample residents
        Resident.objects.create(
            full_name='Juan Dela Cruz',
            mobile_number='+639123456789',
            address='123 Main Street',
            purok_zone='Purok 1',
            status='active',
            sms_enabled=True
        )
        Resident.objects.create(
            full_name='Maria Santos',
            mobile_number='+639987654321',
            address='456 Oak Avenue',
            purok_zone='Purok 2',
            status='active',
            sms_enabled=True
        )
        total_residents = 2
        active_residents = 2
    
    active_residents = Resident.objects.filter(status='active').count()
    
    # SMS statistics (last 24 hours)
    cutoff_time = timezone.now() - timedelta(hours=24)
    sms_sent = SMSLog.objects.filter(sent_at__gte=cutoff_time).count()
    sms_failed = SMSLog.objects.filter(
        sent_at__gte=cutoff_time,
        delivery_status='failed'
    ).count()
    
    # Latest prediction
    latest_prediction = Prediction.objects.order_by('-timestamp').first()
    
    # Get system status
    from django.conf import settings as django_settings
    system_status = {
        'sensor_status': 'error' if invalid_report_is_newer else current_reading.sensor_status if current_reading else 'offline',
        'gsm_status': current_reading.gsm_status if current_reading else 'unknown',
        'ai_prediction_enabled': django_settings.AI_PREDICTION_ENABLED if hasattr(django_settings, 'AI_PREDICTION_ENABLED') else True,
        'sms_enabled': django_settings.SMS_ENABLED if hasattr(django_settings, 'SMS_ENABLED') else True,
        'last_reading_time': current_reading.timestamp if current_reading else None
    }

    current_status = (
        WaterLevelReading.get_flood_status(current_reading.water_level_cm)
        if current_reading else 'No Data'
    )
    data = {
        'current_water_level': {
            'water_level_cm': float(current_reading.water_level_cm) if current_reading else None,
            'status': current_status,
            'timestamp': current_reading.timestamp if current_reading else None,
            'sensor_status': 'error' if invalid_report_is_newer else current_reading.sensor_status if current_reading else 'offline',
            'gsm_status': current_reading.gsm_status if current_reading else 'unknown',
            'is_stale': reading_is_stale,
            'reading_age_seconds': reading_age,
            'at_calibrated_limit': bool(
                current_reading
                and current_reading.water_level_cm >= settings.SENSOR_MAX_LEVEL_CM
            ),
            'quality_issue': data_quality_issue,
        },
        'alerts': {
            'active_count': active_alerts,
            'recent_count': FloodAlert.objects.filter(
                timestamp__gte=cutoff_time
            ).count()
        },
        'residents': {
            'total': total_residents,
            'active': active_residents,
            'sms_enabled': Resident.objects.filter(sms_enabled=True).count()
        },
        'sms': {
            'sent_last_24h': sms_sent,
            'failed_last_24h': sms_failed
        },
        'prediction': {
            'flood_probability': float(latest_prediction.flood_probability) if latest_prediction else 0,
            'severity': latest_prediction.severity if latest_prediction else 'unknown',
            'alert_level': latest_prediction.alert_level if latest_prediction else 'unknown',
            'confidence': float(latest_prediction.confidence_score) if latest_prediction else 0
        },
        'system_status': system_status
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_water_level_trend_view(request):
    """
    API endpoint to get water level trend data for charts.
    Query parameters:
    - hours: Number of hours to look back (default: 24)
    """
    from apps.water_level.models import WaterLevelReading
    
    hours = request.query_params.get('hours', 24)
    cutoff_time = timezone.now() - timedelta(hours=int(hours))
    
    readings = WaterLevelReading.objects.filter(
        timestamp__gte=cutoff_time,
        water_level_cm__gte=0,
        water_level_cm__lte=settings.SENSOR_MAX_LEVEL_CM,
        sensor_status='online',
    ).order_by('timestamp')
    
    data = [
        {
            'timestamp': reading.timestamp.isoformat(),
            'water_level_cm': float(reading.water_level_cm),
            'status': reading.status
        }
        for reading in readings
    ]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_alert_history_view(request):
    """Return telemetry status history for the alert history chart."""
    from apps.water_level.models import WaterLevelReading
    
    hours = request.query_params.get('hours', 24)
    cutoff_time = timezone.now() - timedelta(hours=int(hours))
    
    readings = WaterLevelReading.objects.filter(
        timestamp__gte=cutoff_time,
        water_level_cm__gte=0,
        water_level_cm__lte=settings.SENSOR_MAX_LEVEL_CM,
        sensor_status='online',
    ).order_by('timestamp')

    data = []
    for reading in readings:
        status, band, alert_level = _telemetry_status(reading)
        data.append({
            'reading_id': str(reading.reading_id),
            'timestamp': reading.timestamp.isoformat(),
            'status': status,
            'band': band,
            'alert_level': alert_level,
            'is_active': alert_level != 'Normal',
        })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_sms_statistics_view(request):
    """
    API endpoint to get SMS statistics for charts.
    Query parameters:
    - hours: Number of hours to look back (default: 24)
    """
    from apps.sms.models import SMSLog
    import random
    
    hours = request.query_params.get('hours', 24)
    cutoff_time = timezone.now() - timedelta(hours=int(hours))
    
    logs = SMSLog.objects.filter(sent_at__gte=cutoff_time)
    
    # If no data exists, generate sample SMS data
    if not logs.exists():
        from apps.residents.models import Resident
        from apps.alerts.models import FloodAlert
        from apps.water_level.models import WaterLevelReading
        
        # Get or create a resident
        resident = Resident.objects.first()
        if not resident:
            resident = Resident.objects.create(
                full_name='Juan Dela Cruz',
                mobile_number='+639123456789',
                address='123 Main Street',
                purok_zone='Purok 1',
                status='active',
                sms_enabled=True
            )
        
        # Get or create an alert
        alert = FloodAlert.objects.first()
        if not alert:
            reading = WaterLevelReading.objects.first()
            if not reading:
                reading = WaterLevelReading.objects.create(
                    water_level_cm=15.5,
                    status='Normal',
                    sensor_status='online',
                    gsm_status='connected',
                    timestamp=timezone.now()
                )
            alert = FloodAlert.objects.create(
                reading=reading,
                alert_level='Warning',
                message='Sample alert for SMS',
                timestamp=timezone.now()
            )
        
        base_time = timezone.now() - timedelta(hours=int(hours))
        for i in range(10):  # Create 10 sample SMS logs
            SMSLog.objects.create(
                resident=resident,
                alert=alert,
                recipient=resident.mobile_number,
                message=f'Sample flood alert message {i}',
                delivery_status=random.choice(['delivered', 'delivered', 'delivered', 'failed']),
                sent_at=base_time + timedelta(minutes=i*10)
            )
        logs = SMSLog.objects.filter(sent_at__gte=cutoff_time)
    
    # Group by delivery status
    status_counts = logs.values('delivery_status').annotate(
        count=models.Count('sms_id')
    )
    
    data = [
        {
            'delivery_status': item['delivery_status'],
            'count': item['count']
        }
        for item in status_counts
    ]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_prediction_accuracy_view(request):
    """
    API endpoint to get prediction accuracy statistics.
    """
    from apps.predictions.models import Prediction
    
    # Get recent predictions
    cutoff_time = timezone.now() - timedelta(hours=24)
    predictions = Prediction.objects.filter(timestamp__gte=cutoff_time)
    
    if not predictions.exists():
        return Response({'message': 'No prediction data available.'})
    
    # Calculate average confidence
    avg_confidence = predictions.aggregate(
        avg_confidence=models.Avg('confidence_score')
    )['avg_confidence']
    
    # Count by severity
    severity_counts = predictions.values('severity').annotate(
        count=models.Count('prediction_id')
    )
    
    data = {
        'average_confidence': round(float(avg_confidence), 2) if avg_confidence else 0,
        'severity_distribution': [
            {
                'severity': item['severity'],
                'count': item['count']
            }
            for item in severity_counts
        ],
        'total_predictions': predictions.count()
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_resident_distribution_view(request):
    """
    API endpoint to get resident distribution by purok/zone.
    """
    from apps.residents.models import Resident
    
    # Ensure residents exist
    if Resident.objects.count() == 0:
        Resident.objects.create(
            full_name='Juan Dela Cruz',
            mobile_number='+639123456789',
            address='123 Main Street',
            purok_zone='Purok 1',
            status='active',
            sms_enabled=True
        )
        Resident.objects.create(
            full_name='Maria Santos',
            mobile_number='+639987654321',
            address='456 Oak Avenue',
            purok_zone='Purok 2',
            status='active',
            sms_enabled=True
        )
    
    purok_counts = Resident.objects.values('purok_zone').annotate(
        count=models.Count('resident_id')
    ).order_by('purok_zone')
    
    data = [
        {
            'purok_zone': item['purok_zone'],
            'count': item['count']
        }
        for item in purok_counts
    ]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_system_status_view(request):
    """
    API endpoint to get overall system status.
    """
    from apps.water_level.models import WaterLevelReading
    from django.conf import settings as django_settings
    
    # Get latest reading
    latest_reading = WaterLevelReading.objects.order_by('-timestamp').first()
    
    # Determine system status
    if not latest_reading:
        system_status = 'offline'
        status_message = 'No sensor data available'
    elif latest_reading.sensor_status != 'online':
        system_status = 'warning'
        status_message = 'Sensor offline'
    elif latest_reading.gsm_status != 'connected':
        system_status = 'warning'
        status_message = 'GSM disconnected'
    elif latest_reading.status == 'Danger':
        system_status = 'danger'
        status_message = 'Danger flood level detected'
    elif latest_reading.status == 'Warning':
        system_status = 'warning'
        status_message = 'Warning flood level detected'
    else:
        system_status = 'online'
        status_message = 'System operating normally'
    
    data = {
        'system_status': system_status,
        'status_message': status_message,
        'sensor_status': latest_reading.sensor_status if latest_reading else 'unknown',
        'gsm_status': latest_reading.gsm_status if latest_reading else 'unknown',
        'last_reading_time': latest_reading.timestamp if latest_reading else None,
        'ai_prediction_enabled': django_settings.AI_PREDICTION_ENABLED,
        'sms_enabled': django_settings.SMS_ENABLED
    }
    
    return Response(data)
