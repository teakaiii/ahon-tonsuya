from datetime import timedelta

import numpy as np
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import User
from .forecasting import forecast_water_level


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
