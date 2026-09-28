"""
Views for Settings module.
"""
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import SystemSetting
from .serializers import (
    SystemSettingSerializer,
    SystemSettingCreateSerializer
)


class SystemSettingListView(generics.ListAPIView):
    """
    API endpoint to list all system settings.
    Only admins can access this endpoint.
    """
    serializer_class = SystemSettingSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['key', 'description']
    ordering_fields = ['key', 'updated_at']
    ordering = ['key']
    
    def get_queryset(self):
        # Create sample settings if none exist
        if SystemSetting.objects.count() == 0:
            from django.conf import settings as django_settings
            sample_settings = [
                {'key': 'normal_threshold', 'value': str(django_settings.NORMAL_THRESHOLD), 'description': 'Normal water level threshold (cm)'},
                {'key': 'warning_threshold', 'value': str(django_settings.WARNING_THRESHOLD), 'description': 'Warning begins at 2 cm for the calibrated sensor'},
                {'key': 'danger_threshold', 'value': str(django_settings.DANGER_THRESHOLD), 'description': 'Critical/Danger begins at 3 cm for the calibrated sensor'},
                {'key': 'sms_enabled', 'value': 'true', 'description': 'Enable SMS notifications'},
                {'key': 'ai_prediction_enabled', 'value': 'true', 'description': 'Enable AI flood prediction'},
                {'key': 'reading_interval', 'value': '30', 'description': 'Sensor reading interval (seconds)'},
                {'key': 'sync_interval', 'value': '60', 'description': 'Backend sync interval (seconds)'},
                {'key': 'max_sms_per_hour', 'value': '100', 'description': 'Maximum SMS per hour'},
            ]
            
            for setting in sample_settings:
                SystemSetting.objects.create(
                    key=setting['key'],
                    value=setting['value'],
                    description=setting['description'],
                    updated_by=self.request.user
                )
        
        return SystemSetting.objects.select_related('updated_by').all()


class SystemSettingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint to retrieve, update or delete a system setting.
    Only admins can access this endpoint.
    """
    queryset = SystemSetting.objects.select_related('updated_by').all()
    serializer_class = SystemSettingSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    lookup_field = 'setting_id'
    
    def perform_update(self, serializer):
        # Log activity
        from apps.activity_logs.utils import log_activity
        log_activity(
            user=self.request.user,
            action='update',
            entity='setting',
            entity_id=str(self.get_object().setting_id),
            details=serializer.validated_data
        )
        serializer.save(updated_by=self.request.user)
    
    def perform_destroy(self, instance):
        # Log activity
        from apps.activity_logs.utils import log_activity
        log_activity(
            user=self.request.user,
            action='delete',
            entity='setting',
            entity_id=str(instance.setting_id),
            details={'key': instance.key}
        )
        instance.delete()


class SystemSettingCreateView(generics.CreateAPIView):
    """
    API endpoint to create a system setting.
    Only admins can access this endpoint.
    """
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def perform_create(self, serializer):
        # Log activity
        from apps.activity_logs.utils import log_activity
        log_activity(
            user=self.request.user,
            action='create',
            entity='setting',
            details=serializer.validated_data
        )
        serializer.save(updated_by=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_setting_view(request, key):
    """
    API endpoint to get a specific setting by key.
    """
    try:
        setting = SystemSetting.objects.get(key=key)
        serializer = SystemSettingSerializer(setting)
        return Response(serializer.data)
    except SystemSetting.DoesNotExist:
        return Response(
            {'error': 'Setting not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PUT'])
@permission_classes([permissions.IsAdminUser])
def update_setting_view(request, key):
    """
    API endpoint to update a specific setting by key.
    Only admins can access this endpoint.
    """
    try:
        setting, _ = SystemSetting.objects.get_or_create(
            key=key,
            defaults={
                'value': request.data.get('value', ''),
                'description': request.data.get('description', ''),
            },
        )
        setting.value = request.data.get('value', setting.value)
        if 'description' in request.data:
            setting.description = request.data['description']
        setting.updated_by = request.user
        setting.save()
        
        # Log activity
        from apps.activity_logs.utils import log_activity
        log_activity(
            user=request.user,
            action='update',
            entity='setting',
            entity_id=str(setting.setting_id),
            details={'key': key, 'value': setting.value}
        )
        
        serializer = SystemSettingSerializer(setting)
        return Response(serializer.data)
    except SystemSetting.DoesNotExist:
        return Response(
            {'error': 'Setting not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def flood_thresholds_view(request):
    """
    API endpoint to get flood threshold settings.
    """
    from django.conf import settings as django_settings

    return Response({
        'normal_threshold': django_settings.NORMAL_THRESHOLD,
        'warning_threshold': django_settings.WARNING_THRESHOLD,
        'danger_threshold': django_settings.DANGER_THRESHOLD,
    })
