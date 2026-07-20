from rest_framework import serializers
from .models import Driver, Vehicle, Recording, GPSPoint, EmergencyEvent

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['id', 'name', 'license_number', 'phone', 'profile_picture', 'created_at']

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
    class Meta:
        model = Recording
        fields = [
            'driver', 'vehicle', 'start_time', 'start_latitude',
            'start_longitude', 'is_emergency'
        ]