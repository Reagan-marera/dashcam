import json
import base64
import cv2
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from api.models import Recording, GPSPoint
import datetime
import logging

logger = logging.getLogger(__name__)

class VideoStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'video_stream'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected: {self.channel_name}")
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'video_frame':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'video_frame',
                        'frame': data.get('frame'),
                        'timestamp': data.get('timestamp')
                    }
                )
            
            elif message_type == 'gps_data':
                recording_id = data.get('recording_id')
                if recording_id:
                    await self.save_gps_data(recording_id, data)
                    
                    # Broadcast location update
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'location_update',
                            'latitude': data.get('latitude'),
                            'longitude': data.get('longitude'),
                            'speed': data.get('speed', 0)
                        }
                    )
            
            elif message_type == 'metadata':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'metadata_update',
                        'data': data.get('data')
                    }
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def video_frame(self, event):
        await self.send(text_data=json.dumps({
            'type': 'video_frame',
            'frame': event['frame'],
            'timestamp': event['timestamp']
        }))
    
    async def location_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'speed': event['speed']
        }))
    
    async def metadata_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'metadata',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def save_gps_data(self, recording_id, data):
        try:
            recording = Recording.objects.get(id=recording_id)
            
            # Check if GPS point already exists for this timestamp
            timestamp = datetime.datetime.fromisoformat(data.get('timestamp'))
            
            GPSPoint.objects.create(
                recording=recording,
                timestamp=timestamp,
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                speed_kmh=data.get('speed', 0),
                altitude=data.get('altitude'),
                accuracy=data.get('accuracy'),
                heading=data.get('heading')
            )
            
            # Update recording max speed
            speed = data.get('speed', 0)
            if speed > recording.max_speed_kmh:
                recording.max_speed_kmh = speed
            
            # Update average speed
            all_points = recording.gps_points.all()
            if all_points.count() > 0:
                from django.db.models import Avg
                avg_speed = all_points.aggregate(Avg('speed_kmh'))['speed_kmh__avg']
                if avg_speed:
                    recording.avg_speed_kmh = avg_speed
            
            recording.save()
            
        except Recording.DoesNotExist:
            logger.error(f"Recording {recording_id} not found")
        except Exception as e:
            logger.error(f"Error saving GPS data: {e}")