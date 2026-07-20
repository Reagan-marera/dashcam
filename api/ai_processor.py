import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import os
from django.conf import settings
import json

class DashcamAIProcessor:
    def __init__(self):
        # Load YOLO model - will download if not present
        self.yolo_model = YOLO('yolov8n.pt')
        self.reader = easyocr.Reader(['en'])
        print("AI Models loaded successfully")
        
    def process_video(self, recording_id):
        from api.models import Recording
        
        try:
            recording = Recording.objects.get(id=recording_id)
            video_path = recording.video_file.path
            
            if not os.path.exists(video_path):
                return {'error': 'Video file not found'}
            
            cap = cv2.VideoCapture(video_path)
            detections = []
            frame_count = 0
            processed_frames = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process every 15th frame
                if frame_count % 15 == 0:
                    frame_detections = self.process_frame(frame, frame_count)
                    if frame_detections:
                        detections.extend(frame_detections)
                    processed_frames += 1
                
                frame_count += 1
                
                # Limit processing to avoid memory issues
                if frame_count > 1500:  # ~1 minute at 25fps
                    break
            
            cap.release()
            
            # Save results
            recording.detections = {
                'total_frames': frame_count,
                'processed_frames': processed_frames,
                'detections': detections,
                'object_counts': self.count_objects(detections),
                'summary': self.generate_summary(detections)
            }
            recording.is_processed = True
            recording.save()
            
            return {
                'status': 'success',
                'total_frames': frame_count,
                'processed_frames': processed_frames,
                'detections_count': len(detections),
                'object_counts': recording.detections['object_counts']
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def process_frame(self, frame, frame_number):
        detections = []
        
        try:
            # Resize for faster processing
            height, width = frame.shape[:2]
            if width > 640:
                scale = 640 / width
                new_width = 640
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # YOLO detection
            results = self.yolo_model(frame, verbose=False)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        confidence = float(box.conf[0].tolist())
                        class_id = int(box.cls[0].tolist())
                        class_name = self.yolo_model.names[class_id]
                        
                        # Filter low confidence
                        if confidence < 0.5:
                            continue
                        
                        detection = {
                            'frame': frame_number,
                            'class': class_name,
                            'confidence': confidence,
                            'bbox': [float(x1), float(y1), float(x2), float(y2)]
                        }
                        
                        # Try to read license plate for vehicles
                        if class_name in ['car', 'truck', 'motorcycle', 'bus']:
                            vehicle_roi = frame[int(y1):int(y2), int(x1):int(x2)]
                            if vehicle_roi.size > 0:
                                plate_text = self.read_license_plate(vehicle_roi)
                                if plate_text:
                                    detection['license_plate'] = plate_text
                        
                        detections.append(detection)
                        
        except Exception as e:
            print(f"Error processing frame {frame_number}: {e}")
        
        return detections
    
    def read_license_plate(self, roi):
        try:
            # Preprocess for better OCR
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Try different thresholding methods
            _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY, 11, 2)
            
            # Try both
            for thresh in [thresh1, thresh2]:
                results = self.reader.readtext(thresh, paragraph=False)
                for (bbox, text, confidence) in results:
                    # Clean text
                    clean_text = ''.join(e for e in text if e.isalnum()).upper()
                    if len(clean_text) >= 4 and confidence > 0.4:
                        return clean_text
            
            return None
        except Exception as e:
            print(f"Error reading plate: {e}")
            return None
    
    def count_objects(self, detections):
        counts = {}
        for detection in detections:
            class_name = detection['class']
            counts[class_name] = counts.get(class_name, 0) + 1
        return counts
    
    def generate_summary(self, detections):
        summary = {
            'total_detections': len(detections),
            'unique_objects': len(set(d['class'] for d in detections)),
            'license_plates_detected': sum(1 for d in detections if 'license_plate' in d),
            'time_range': {
                'start_frame': detections[0]['frame'] if detections else None,
                'end_frame': detections[-1]['frame'] if detections else None
            }
        }
        return summary