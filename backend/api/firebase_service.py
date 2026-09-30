"""
Firebase Realtime Database Service for Django.
This module handles all Firebase operations including:
- Reading water level data from Firebase
- Syncing data to PostgreSQL
- Listening for real-time updates
"""

import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings
import logging
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils import timezone

logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Firebase Realtime Database Service.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.initialize_firebase()
            self._initialized = True
    
    def initialize_firebase(self):
        """
        Initialize Firebase Admin SDK.
        """
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(settings.FIREBASE_PRIVATE_KEY_PATH)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': settings.FIREBASE_DATABASE_URL
                })
                logger.info("Firebase initialized successfully")
            else:
                logger.info("Firebase already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    def get_current_water_level(self):
        """
        Get current water level from Firebase.
        
        Returns:
            dict: Water level data or None if not available
        """
        try:
            ref = db.reference('water_level')
            data = ref.get()
            
            if data:
                logger.info(f"Retrieved water level from Firebase: {data}")
                return data
            else:
                logger.warning("No water level data found in Firebase")
                return None
        except Exception as e:
            logger.error(f"Failed to get water level from Firebase: {e}")
            return None
    
    def get_water_level_history(self, limit=100):
        """
        Get water level history from Firebase.
        
        Args:
            limit: Maximum number of records to retrieve
            
        Returns:
            list: List of water level readings
        """
        try:
            ref = db.reference('water_level_history')
            data = ref.order_by_child('timestamp').limit_to_last(limit).get()
            
            if data:
                readings = []
                for key, value in data.items():
                    readings.append(value)
                logger.info(f"Retrieved {len(readings)} water level readings from Firebase")
                return readings
            else:
                logger.warning("No water level history found in Firebase")
                return []
        except Exception as e:
            logger.error(f"Failed to get water level history from Firebase: {e}")
            return []
    
    def get_alerts(self):
        """
        Get alerts from Firebase.
        
        Returns:
            dict: Alerts data or None if not available
        """
        try:
            ref = db.reference('alerts')
            data = ref.get()
            
            if data:
                logger.info(f"Retrieved alerts from Firebase: {len(data)} alerts")
                return data
            else:
                logger.warning("No alerts found in Firebase")
                return None
        except Exception as e:
            logger.error(f"Failed to get alerts from Firebase: {e}")
            return None
    
    def get_sms_logs(self):
        """
        Get SMS logs from Firebase.
        
        Returns:
            dict: SMS logs data or None if not available
        """
        try:
            ref = db.reference('sms_logs')
            data = ref.get()
            
            if data:
                logger.info(f"Retrieved SMS logs from Firebase: {len(data)} logs")
                return data
            else:
                logger.warning("No SMS logs found in Firebase")
                return None
        except Exception as e:
            logger.error(f"Failed to get SMS logs from Firebase: {e}")
            return None
    
    def sync_water_level_to_postgres(self, firebase_data):
        """
        Sync water level data from Firebase to PostgreSQL.
        
        Args:
            firebase_data: Water level data from Firebase
            
        Returns:
            WaterLevelReading: Created reading object or None
        """
        try:
            from apps.water_level.models import WaterLevelReading
            
            # Parse Firebase data
            water_level_cm = firebase_data.get(
                'current_level',
                firebase_data.get('water_level_cm', firebase_data.get('water_level')),
            )
            timestamp_str = firebase_data.get('timestamp')
            
            if water_level_cm is None or timestamp_str is None:
                logger.warning("Incomplete water level data from Firebase")
                return None

            try:
                water_level_cm = Decimal(str(water_level_cm))
            except (InvalidOperation, TypeError, ValueError):
                logger.warning("Invalid water level data from Firebase: %r", water_level_cm)
                return None

            maximum = Decimal(str(settings.SENSOR_MAX_LEVEL_CM))
            if not water_level_cm.is_finite() or not 0 <= water_level_cm <= maximum:
                logger.warning(
                    "Firebase water level is outside the calibrated 0-%s cm range: %s",
                    maximum,
                    water_level_cm,
                )
                return None
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(str(timestamp_str).replace('Z', '+00:00'))
            if timezone.is_naive(timestamp):
                timestamp = timezone.make_aware(timestamp)

            status = WaterLevelReading.get_flood_status(water_level_cm)
            
            # Check if reading already exists
            existing = WaterLevelReading.objects.filter(
                water_level_cm=water_level_cm,
                timestamp=timestamp
            ).first()
            
            if existing:
                logger.info(f"Reading already exists in PostgreSQL: {existing.reading_id}")
                existing.firebase_synced = True
                existing.status = status
                existing.save(update_fields=['firebase_synced', 'status'])
                return existing
            
            # Create new reading
            reading = WaterLevelReading.objects.create(
                water_level_cm=water_level_cm,
                status=status,
                timestamp=timestamp,
                sensor_status='online',
                gsm_status='connected',
                firebase_synced=True
            )
            
            logger.info(f"Synced water level to PostgreSQL: {reading.reading_id}")
            return reading
            
        except Exception as e:
            logger.error(f"Failed to sync water level to PostgreSQL: {e}")
            return None
    
    def sync_alerts_to_postgres(self, firebase_alerts):
        """
        Sync alerts from Firebase to PostgreSQL.
        
        Args:
            firebase_alerts: Alerts data from Firebase
            
        Returns:
            int: Number of alerts synced
        """
        try:
            from apps.alerts.models import FloodAlert
            from apps.water_level.models import WaterLevelReading
            
            synced_count = 0
            
            if not firebase_alerts:
                return synced_count
            
            for alert_key, alert_data in firebase_alerts.items():
                try:
                    # Get associated reading
                    reading = WaterLevelReading.objects.filter(
                        timestamp__gte=alert_data.get('timestamp')
                    ).first()
                    
                    if not reading:
                        continue
                    
                    # Check if alert already exists
                    existing = FloodAlert.objects.filter(
                        reading=reading,
                        alert_level=alert_data.get('alert_level'),
                        timestamp=alert_data.get('timestamp')
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Create new alert
                    FloodAlert.objects.create(
                        reading=reading,
                        alert_level=alert_data.get('alert_level'),
                        message=alert_data.get('message'),
                        timestamp=alert_data.get('timestamp')
                    )
                    
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync alert {alert_key}: {e}")
                    continue
            
            logger.info(f"Synced {synced_count} alerts to PostgreSQL")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync alerts to PostgreSQL: {e}")
            return 0
    
    def listen_to_water_level(self, callback):
        """
        Listen to real-time water level updates from Firebase.
        
        Args:
            callback: Function to call when data changes
        """
        try:
            ref = db.reference('water_level')
            
            def listener(event):
                try:
                    if event.data:
                        logger.info(f"Water level updated in Firebase: {event.data}")
                        callback(event.data)
                except Exception as e:
                    logger.error(f"Error in water level listener callback: {e}")
            
            ref.listen(listener)
            logger.info("Started listening to water level updates")
            
        except Exception as e:
            logger.error(f"Failed to start water level listener: {e}")
    
    def stop_listening(self):
        """
        Stop all Firebase listeners.
        """
        try:
            # Firebase Admin SDK doesn't have a direct stop listening method
            # This is a placeholder for cleanup
            logger.info("Stopped Firebase listeners")
        except Exception as e:
            logger.error(f"Failed to stop Firebase listeners: {e}")
    
    def test_connection(self):
        """
        Test Firebase connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            ref = db.reference('test')
            ref.set({'test': True, 'timestamp': datetime.now().isoformat()})
            data = ref.get()
            
            if data:
                logger.info("Firebase connection test successful")
                ref.delete()
                return True
            else:
                logger.error("Firebase connection test failed: No data returned")
                return False
        except Exception as e:
            logger.error(f"Firebase connection test failed: {e}")
            return False


# Singleton instance
firebase_service = FirebaseService()
