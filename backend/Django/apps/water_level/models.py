"""
Water Level models for sensor readings.
"""
from django.db import models
from django.conf import settings
import uuid


class WaterLevelReading(models.Model):
    """
    Model to store water level sensor readings.
    """
    STATUS_CHOICES = [
        ('Normal', 'Normal'),
        ('Alert', 'Alert'),
        ('Warning', 'Warning'),
        ('Danger', 'Danger'),
    ]
    
    SENSOR_STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
    ]
    
    GSM_STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ]
    
    reading_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    water_level_cm = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField()
    sensor_status = models.CharField(max_length=20, choices=SENSOR_STATUS_CHOICES, default='online')
    gsm_status = models.CharField(max_length=20, choices=GSM_STATUS_CHOICES, default='connected')
    firebase_synced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'water_level_readings'
        verbose_name = 'Water Level Reading'
        verbose_name_plural = 'Water Level Readings'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['status']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.water_level_cm}cm - {self.status} at {self.timestamp}"
    
    @classmethod
    def get_flood_status(cls, water_level):
        """
        Determine flood status based on water level.
        """
        if water_level >= settings.DANGER_THRESHOLD:
            return 'Danger'
        if water_level >= settings.WARNING_THRESHOLD:
            return 'Warning'
        return 'Normal'
