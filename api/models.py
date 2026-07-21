from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver')
    name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15)
    profile_picture = models.ImageField(upload_to='drivers/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('truck', 'Truck'),
        ('motorcycle', 'Motorcycle'),
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('other', 'Other'),
    ]
    
    registration = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=100)
    make = models.CharField(max_length=100)
    year = models.IntegerField()
    color = models.CharField(max_length=30)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='car')
    owner = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='vehicles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.registration} - {self.make} {self.model}"

class Recording(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='recordings')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='recordings')
    
    video_file = models.FileField(upload_to='recordings/videos/%Y/%m/%d/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='recordings/thumbnails/%Y/%m/%d/', null=True, blank=True)
    
    date = models.DateField(auto_now_add=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    start_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    start_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    
    avg_speed_kmh = models.FloatField(default=0)
    max_speed_kmh = models.FloatField(default=0)
    
    file_size_mb = models.FloatField(default=0)
    is_emergency = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    
    detections = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.driver.name} - {self.date} - {self.start_time}"
    
    class Meta:
        ordering = ['-created_at']

class GPSPoint(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE, related_name='gps_points')
    timestamp = models.DateTimeField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    speed_kmh = models.FloatField()
    altitude = models.FloatField(null=True, blank=True)
    accuracy = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.recording.id} - {self.timestamp}"
    
    class Meta:
        ordering = ['timestamp']

class EmergencyEvent(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE, related_name='emergency_events')
    timestamp = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    speed_kmh = models.FloatField()
    description = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Emergency {self.id} - {self.recording.driver.name}"