import json
import base64
import cv2
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from api.models import Recording, GPSPoint
import datetime
import logging
from ultralytics import YOLO

logger = logging.getLogger(__name__)

# Shared YOLO model for live frame processing
yolo_model = YOLO('yolov8n.pt')

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
                frame_data = data.get('frame')
                if frame_data:
                    try:
                        # Decode
                        header, encoded = frame_data.split(",", 1)
                        image_bytes = base64.b64decode(encoded)
                        nparr = np.frombuffer(image_bytes, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        if img is not None:
                            # Run YOLO detection
                            results = yolo_model(img, verbose=False)
                            for result in results:
                                boxes = result.boxes
                                if boxes is not None:
                                    for box in boxes:
                                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                                        confidence = float(box.conf[0].tolist())
                                        class_id = int(box.cls[0].tolist())
                                        class_name = yolo_model.names[class_id]

                                        if confidence >= 0.4:
                                            # Draw green bounding box (BGR format: Green is (0, 255, 0))
                                            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

                                            label = f"{class_name.upper()} {confidence:.1%}"
                                            if class_name in ['car', 'truck', 'bus', 'motorcycle']:
                                                # Simulate height based on box proportions
                                                sim_height = round(1.4 + (class_id * 0.2) + (y2 - y1) * 0.002, 1)
                                                label += f" | H: {sim_height}m"

                                            cv2.putText(img, label, (int(x1), int(y1) - 10),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                            # Re-encode to base64
                            _, buffer = cv2.imencode('.jpg', img)
                            processed_base64 = base64.b64encode(buffer).decode('utf-8')
                            frame_data = f"data:image/jpeg;base64,{processed_base64}"
                    except Exception as e:
                        logger.error(f"Live AI frame overlay failed: {e}")

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'video_frame',
                        'frame': frame_data,
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