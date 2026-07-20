from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import os
import cv2
import numpy as np
from .models import Driver, Vehicle, Recording, GPSPoint, EmergencyEvent
from .serializers import (
    DriverSerializer, VehicleSerializer, RecordingSerializer, 
    RecordingCreateSerializer, GPSPointSerializer, EmergencyEventSerializer
)

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [AllowAny]

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        owner_id = self.request.query_params.get('owner')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        return queryset

class RecordingViewSet(viewsets.ModelViewSet):
    queryset = Recording.objects.all()
    serializer_class = RecordingSerializer
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RecordingCreateSerializer
        return RecordingSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        video_file = request.FILES.get('video_file')
        if not video_file:
            return Response(
                {'error': 'Video file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recording = serializer.save(video_file=video_file)
        recording.file_size_mb = video_file.size / (1024 * 1024)
        recording.save()
        
        return Response(
            RecordingSerializer(recording).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def add_gps_data(self, request, pk=None):
        recording = self.get_object()
        serializer = GPSPointSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(recording=recording)
            
            if not recording.end_time or serializer.validated_data['timestamp'] > recording.end_time:
                recording.end_time = serializer.validated_data['timestamp']
            
            if serializer.validated_data['speed_kmh'] > recording.max_speed_kmh:
                recording.max_speed_kmh = serializer.validated_data['speed_kmh']
            
            # Update average speed
            all_points = recording.gps_points.all()
            if all_points.count() > 0:
                avg_speed = all_points.aggregate(models.Avg('speed_kmh'))['speed_kmh__avg']
                recording.avg_speed_kmh = avg_speed or 0
            
            recording.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_emergency(self, request, pk=None):
        recording = self.get_object()
        serializer = EmergencyEventSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(recording=recording)
            recording.is_emergency = True
            recording.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        driver_id = request.query_params.get('driver_id')
        vehicle_id = request.query_params.get('vehicle_id')
        is_emergency = request.query_params.get('is_emergency')
        
        recordings = self.get_queryset()
        
        if query:
            recordings = recordings.filter(
                Q(driver__name__icontains=query) |
                Q(vehicle__registration__icontains=query) |
                Q(vehicle__model__icontains=query) |
                Q(vehicle__make__icontains=query)
            )
        
        if start_date:
            recordings = recordings.filter(date__gte=start_date)
        
        if end_date:
            recordings = recordings.filter(date__lte=end_date)
        
        if driver_id:
            recordings = recordings.filter(driver_id=driver_id)
        
        if vehicle_id:
            recordings = recordings.filter(vehicle_id=vehicle_id)
        
        if is_emergency is not None:
            recordings = recordings.filter(is_emergency=is_emergency.lower() == 'true')
        
        page = self.paginate_queryset(recordings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recordings, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        recording = self.get_object()
        
        if recording.video_file:
            return Response({
                'download_url': recording.video_file.url,
                'file_name': os.path.basename(recording.video_file.name),
                'file_size_mb': recording.file_size_mb
            })
        
        return Response(
            {'error': 'No video file found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['get'])
    def export_gps(self, request, pk=None):
        recording = self.get_object()
        gps_points = recording.gps_points.all()
        
        data = [
            {
                'timestamp': point.timestamp.isoformat(),
                'latitude': float(point.latitude),
                'longitude': float(point.longitude),
                'speed_kmh': point.speed_kmh,
                'altitude': point.altitude,
                'heading': point.heading
            }
            for point in gps_points
        ]
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def process_ai(self, request, pk=None):
        from recordings.ai_processor import DashcamAIProcessor
        
        recording = self.get_object()
        
        if not recording.video_file:
            return Response(
                {'error': 'No video file to process'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            processor = DashcamAIProcessor()
            result = processor.process_video(str(recording.id))
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )