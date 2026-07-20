from django.contrib import admin
from .models import Driver, Vehicle, Recording, GPSPoint, EmergencyEvent

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'license_number', 'phone', 'created_at')
    search_fields = ('name', 'license_number', 'phone')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration', 'make', 'model', 'year', 'color', 'vehicle_type', 'owner')
    search_fields = ('registration', 'make', 'model', 'owner__name')
    list_filter = ('vehicle_type', 'color', 'year')

@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver', 'vehicle', 'date', 'start_time', 'end_time', 'duration_seconds', 'avg_speed_kmh', 'max_speed_kmh', 'is_emergency', 'is_processed')
    search_fields = ('driver__name', 'vehicle__registration', 'id')
    list_filter = ('is_emergency', 'is_processed', 'date')

@admin.register(GPSPoint)
class GPSPointAdmin(admin.ModelAdmin):
    list_display = ('id', 'recording', 'timestamp', 'latitude', 'longitude', 'speed_kmh', 'altitude', 'heading')
    search_fields = ('recording__id', 'recording__driver__name')
    list_filter = ('timestamp',)

@admin.register(EmergencyEvent)
class EmergencyEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'recording', 'timestamp', 'latitude', 'longitude', 'speed_kmh', 'is_resolved', 'resolved_at')
    search_fields = ('recording__id', 'recording__driver__name', 'description')
    list_filter = ('is_resolved', 'timestamp')
