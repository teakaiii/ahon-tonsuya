import calendar
from datetime import datetime, timedelta

import numpy as np
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.water_level.models import WaterLevelReading
from .forecasting import forecast_month_profile, forecast_water_level


class WaterLevelForecastServiceTests(SimpleTestCase):
    def test_insufficient_valid_history_returns_reason(self):
        start = timezone.now()
        readings = [
            (start + timedelta(seconds=30 * index), 1.0)
            for index in range(30)
        ]

        result = forecast_water_level(readings)

        self.assertFalse(result['available'])
        self.assertIn('continuous forecast rows', result['reason'])

    def test_out_of_range_readings_are_excluded(self):
        start = timezone.now()
        readings = [
            (start + timedelta(seconds=30 * index), 500.0)
            for index in range(100)
        ]

        result = forecast_water_level(readings)

        self.assertFalse(result['available'])
        self.assertEqual(result['valid_readings'], 0)
        self.assertEqual(result['excluded_readings'], 100)

    def test_forecast_reports_holdout_and_baseline_metrics(self):
        start = timezone.now()
        readings = [
            (
                start + timedelta(seconds=30 * index),
                1.5 + 0.3 * np.sin(index / 80),
            )
            for index in range(600)
        ]

        result = forecast_water_level(readings)

        self.assertTrue(result['available'])
        self.assertEqual(result['unit'], 'cm')
        self.assertEqual(result['valid_readings'], 600)
        self.assertEqual(result['excluded_readings'], 0)
        self.assertIn('mae_cm', result['model_metrics'])
        self.assertIn('mae_cm', result['baseline_metrics'])
        self.assertIn(result['selected_method'], {'random_forest', 'persistence_baseline'})
        self.assertGreaterEqual(result['selected_forecast_cm'], 0)
        self.assertLessEqual(result['selected_forecast_cm'], 4)


class MonthlyWaterLevelForecastTests(SimpleTestCase):
    def _next_month_start(self):
        today = timezone.localdate()
        return (today.replace(day=28) + timedelta(days=4)).replace(day=1)

    def test_month_profile_reports_metrics_for_exact_forecast_horizons(self):
        forecast_start = self._next_month_start()
        history_days = 90
        first_day = forecast_start - timedelta(days=history_days)
        readings = [
            (
                timezone.make_aware(datetime.combine(first_day + timedelta(days=index), datetime.min.time())),
                1.0 + index / 100,
            )
            for index in range(history_days)
        ]

        result = forecast_month_profile(readings, forecast_start.year, forecast_start.month)

        self.assertTrue(result['available'])
        self.assertEqual(result['history_days'], history_days)
        self.assertEqual(result['training_days'], history_days)
        self.assertEqual(result['forecast_horizon_days'], len(result['points']))
        self.assertEqual(result['validation_days'], result['backtest_folds'])
        self.assertGreaterEqual(result['validation_days'], 5)
        self.assertEqual(result['horizon_metrics']['1']['sample_count'], 12)
        self.assertEqual(
            result['horizon_metrics'][str(len(result['points']))]['sample_count'],
            result['validation_days'],
        )
        self.assertEqual(result['horizon_metrics']['30']['horizon_days'], 30)
        self.assertIn('trend_rmse_cm', result['horizon_metrics']['7'])
        self.assertIn(result['method'], {'linear_trend', 'recent_7_day_average'})
        self.assertGreaterEqual(result['validation_mae_cm'], 0)
        self.assertGreaterEqual(result['validation_rmse_cm'], 0)
        self.assertEqual(result['points'][0]['day'], 1)
        self.assertIsNotNone(result['points'][0]['forecast_cm'])

    def test_month_profile_is_unavailable_without_enough_history_to_validate(self):
        forecast_start = self._next_month_start()
        first_day = forecast_start - timedelta(days=8)
        readings = [
            (
                timezone.make_aware(datetime.combine(first_day + timedelta(days=index), datetime.min.time())),
                2.0,
            )
            for index in range(8)
        ]

        result = forecast_month_profile(readings, forecast_start.year, forecast_start.month)

        self.assertFalse(result['available'])
        self.assertEqual(result['history_days'], 8)
        self.assertIn('at least 5 historical', result['reason'])

    def test_month_profile_requires_five_exact_month_horizon_examples(self):
        forecast_start = self._next_month_start()
        history_days = 40
        first_day = forecast_start - timedelta(days=history_days)
        readings = [
            (
                timezone.make_aware(datetime.combine(first_day + timedelta(days=index), datetime.min.time())),
                1.5,
            )
            for index in range(history_days)
        ]

        result = forecast_month_profile(readings, forecast_start.year, forecast_start.month)

        self.assertFalse(result['available'])
        month_horizon_days = calendar.monthrange(
            forecast_start.year, forecast_start.month
        )[1]
        self.assertLess(result['horizon_metrics'][str(month_horizon_days)]['sample_count'], 5)

    def test_month_profile_skips_missing_exact_horizon_dates(self):
        forecast_start = self._next_month_start()
        history_days = 90
        first_day = forecast_start - timedelta(days=history_days)
        missing_day_index = 13
        readings = [
            (
                timezone.make_aware(datetime.combine(first_day + timedelta(days=index), datetime.min.time())),
                1.0 + index / 100,
            )
            for index in range(history_days)
            if index != missing_day_index
        ]

        result = forecast_month_profile(readings, forecast_start.year, forecast_start.month)

        self.assertTrue(result['available'])
        self.assertEqual(result['horizon_metrics']['7']['sample_count'], 10)


class WaterLevelForecastAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_forecast_requires_authentication(self):
        response = self.client.get('/api/dashboard/water-level-forecast/')

        self.assertEqual(response.status_code, 401)

    def test_empty_history_returns_unavailable_instead_of_fake_forecast(self):
        user = User.objects.create_user(
            username='forecast-admin',
            email='forecast-admin@example.com',
            password='test-password',
            role='admin',
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(
            '/api/dashboard/water-level-forecast/',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['available'])
        self.assertEqual(response.data['raw_readings'], 0)

    def test_monthly_forecast_requires_authentication(self):
        response = self.client.get('/api/dashboard/monthly-water-level-forecast/?year=2027&month=1')

        self.assertEqual(response.status_code, 401)

    def test_monthly_forecast_uses_other_months_and_returns_accuracy(self):
        user = User.objects.create_user(
            username='monthly-forecast-admin',
            email='monthly-forecast-admin@example.com',
            password='test-password',
            role='admin',
        )
        self.client.force_authenticate(user=user)
        forecast_start = (timezone.localdate().replace(day=28) + timedelta(days=4)).replace(day=1)
        history_days = 90
        first_day = forecast_start - timedelta(days=history_days)
        WaterLevelReading.objects.bulk_create([
            WaterLevelReading(
                water_level_cm=1.0 + index / 100,
                status='Normal',
                timestamp=timezone.make_aware(datetime.combine(
                    first_day + timedelta(days=index), datetime.min.time()
                )),
            )
            for index in range(history_days)
        ])

        response = self.client.get(
            f'/api/dashboard/monthly-water-level-forecast/?year={forecast_start.year}&month={forecast_start.month}',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['available'])
        self.assertEqual(response.data['history_days'], history_days)
        self.assertIn('validation_mae_cm', response.data)
        self.assertIn('horizon_metrics', response.data)
        self.assertIn(str(len(response.data['points'])), response.data['horizon_metrics'])


class DashboardWaterLevelDataTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(
            username='dashboard-water-admin',
            email='dashboard-water-admin@example.com',
            password='test-password',
            role='admin',
        )
        self.client.force_authenticate(user=user)

    def test_empty_dashboard_has_no_fabricated_water_level_or_history(self):
        overview = self.client.get('/api/dashboard/overview/')
        telemetry = self.client.get('/api/dashboard/telemetry/')
        trend = self.client.get('/api/dashboard/water-level-trend/')

        self.assertEqual(overview.status_code, 200)
        self.assertIsNone(overview.data['current_water_level']['water_level_cm'])
        self.assertEqual(overview.data['current_water_level']['status'], 'No Data')
        self.assertTrue(overview.data['current_water_level']['is_stale'])
        self.assertEqual(telemetry.data, [])
        self.assertEqual(trend.data, [])
        self.assertEqual(WaterLevelReading.objects.count(), 0)

    def test_out_of_range_latest_report_is_not_shown_as_current_telemetry(self):
        now = timezone.now()
        valid_reading = WaterLevelReading.objects.create(
            water_level_cm=3.5,
            status='Normal',
            sensor_status='online',
            gsm_status='connected',
            timestamp=now - timedelta(seconds=5),
        )
        WaterLevelReading.objects.create(
            water_level_cm=4.26,
            status='Danger',
            sensor_status='online',
            gsm_status='connected',
            timestamp=now,
        )

        overview = self.client.get('/api/dashboard/overview/')
        telemetry = self.client.get('/api/dashboard/telemetry/?limit=5')

        current = overview.data['current_water_level']
        self.assertEqual(current['water_level_cm'], 3.5)
        self.assertEqual(current['status'], 'Danger')
        self.assertTrue(current['is_stale'])
        self.assertIn('outside the calibrated', current['quality_issue'])
        self.assertEqual(len(telemetry.data), 1)
        self.assertEqual(telemetry.data[0]['reading_id'], str(valid_reading.reading_id))
        self.assertEqual(telemetry.data[0]['water_level_cm'], 3.5)

    def test_full_scale_reading_is_flagged_as_possibly_saturated(self):
        WaterLevelReading.objects.create(
            water_level_cm=4.0,
            status='Danger',
            sensor_status='online',
            gsm_status='connected',
            timestamp=timezone.now(),
        )

        response = self.client.get('/api/dashboard/overview/')

        current = response.data['current_water_level']
        self.assertEqual(current['water_level_cm'], 4.0)
        self.assertTrue(current['at_calibrated_limit'])
        self.assertIn('actual level may be higher', current['quality_issue'])
