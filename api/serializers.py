from rest_framework import serializers
from .models import Driver, Vehicle, Recording, GPSPoint, EmergencyEvent

from django.contrib.auth.models import User

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['id', 'name', 'license_number', 'phone', 'profile_picture', 'created_at']

    def create(self, validated_data):
        username = validated_data.get('license_number', '').replace(' ', '_').lower()
        if not username:
            import uuid
            username = f"user_{uuid.uuid4().hex[:10]}"
        user, _ = User.objects.get_or_create(username=username)
        validated_data['user'] = user
        return super().create(validated_data)

class VehicleSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.name', read_only=True)
    
    class Meta:
        model = Vehicle
        fields = ['id', 'registration', 'model', 'make', 'year', 'color', 'vehicle_type', 'owner', 'owner_name']

class GPSPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSPoint
        fields = ['id', 'timestamp', 'latitude', 'longitude', 'speed_kmh', 'altitude', 'accuracy', 'heading']

class EmergencyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyEvent
        fields = ['id', 'timestamp', 'latitude', 'longitude', 'speed_kmh', 'description', 'is_resolved', 'resolved_at']

class RecordingSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    vehicle_registration = serializers.CharField(source='vehicle.registration', read_only=True)
    gps_points = GPSPointSerializer(many=True, read_only=True)
    emergency_events = EmergencyEventSerializer(many=True, read_only=True)
    
    class Meta:
        model = Recording
        fields = [
            'id', 'driver', 'driver_name', 'vehicle', 'vehicle_registration',
            'video_file', 'thumbnail', 'date', 'start_time', 'end_time',
            'duration_seconds', 'start_latitude', 'start_longitude',
            'avg_speed_kmh', 'max_speed_kmh', 'file_size_mb',
            'is_emergency', 'is_processed', 'detections',
            'gps_points', 'emergency_events', 'created_at'
        ]
        read_only_fields = ['id', 'date', 'created_at']

class RecordingCreateSerializer(serializers.ModelSerializer):
    vehicle_registration = serializers.CharField(write_only=True, required=False)
    vehicle = serializers.PrimaryKeyRelatedField(queryset=Vehicle.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Recording
        fields = [
            'driver', 'vehicle', 'vehicle_registration', 'start_time', 'start_latitude',
            'start_longitude', 'is_emergency'
        ]

    def create(self, validated_data):
        vehicle_reg = validated_data.pop('vehicle_registration', None)
        driver = validated_data.get('driver')

        if vehicle_reg:
            vehicle_reg_clean = vehicle_reg.upper().strip()
            # Look up or create the vehicle under this driver
            vehicle, _ = Vehicle.objects.get_or_create(
                registration=vehicle_reg_clean,
                defaults={
                    'owner': driver,
                    'make': 'Universal',
                    'model': 'Dashcam Vehicle',
                    'year': 2024,
                    'color': 'Black',
                    'vehicle_type': 'car'
                }
            )
            validated_data['vehicle'] = vehicle
        elif not validated_data.get('vehicle'):
            # Fallback to default vehicle 1 or create one
            vehicle, _ = Vehicle.objects.get_or_create(
                id=1,
                defaults={
                    'registration': 'ABC-1234',
                    'owner': driver,
                    'make': 'Universal',
                    'model': 'Dashcam Vehicle',
                    'year': 2024,
                    'color': 'Black',
                    'vehicle_type': 'car'
                }
            )
            validated_data['vehicle'] = vehicle

        return super().create(validated_data)