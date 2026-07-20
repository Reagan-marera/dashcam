import uuid
import datetime
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from api.models import Driver, Vehicle, Recording, GPSPoint, EmergencyEvent

class DashcamAPITests(APITestCase):
    def setUp(self):
        # Create a user and driver
        self.user = User.objects.create_user(username='test_driver_user', password='password123')
        self.driver = Driver.objects.create(
            user=self.user,
            name='Test Driver',
            license_number='LIC-12345',
            phone='1234567890'
        )

        # Create a vehicle
        self.vehicle = Vehicle.objects.create(
            registration='XYZ-789',
            model='Corolla',
            make='Toyota',
            year=2021,
            color='Red',
            vehicle_type='car',
            owner=self.driver
        )

    def test_driver_serializer_autocreate_user(self):
        # Test that driver serializer automatically creates a user if not provided
        url = reverse('driver-list')
        data = {
            'name': 'New Driver',
            'license_number': 'LIC-99999',
            'phone': '0987654321'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Driver.objects.filter(name='New Driver').count(), 1)

        # Verify user was auto-created with username derived from license_number
        username = 'lic-99999'
        self.assertTrue(User.objects.filter(username=username).exists())

    def test_vehicle_list_and_create(self):
        # Get vehicles list
        url = reverse('vehicle-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Create a new vehicle
        data = {
            'registration': 'NEW-777',
            'model': 'Model S',
            'make': 'Tesla',
            'year': 2023,
            'color': 'White',
            'vehicle_type': 'car',
            'owner': self.driver.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vehicle.objects.filter(registration='NEW-777').count(), 1)

    def test_recording_endpoints(self):
        # Test creation of a recording without a video file (should fail with 400)
        url = reverse('recording-list')
        data = {
            'driver': self.driver.id,
            'vehicle': self.vehicle.id,
            'start_time': timezone.now().isoformat(),
            'start_latitude': 37.7749,
            'start_longitude': -122.4194,
            'is_emergency': False
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Video file is required', response.data['error'])

        # Create a mock video file and upload it
        from django.core.files.uploadedfile import SimpleUploadedFile
        video_content = b'fake-video-bytes'
        video_file = SimpleUploadedFile('test_video.mp4', video_content, content_type='video/mp4')

        data['video_file'] = video_file
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recording_id = response.data['id']

        # Add GPS data
        gps_url = reverse('recording-add-gps-data', args=[recording_id])
        gps_data = {
            'timestamp': timezone.now().isoformat(),
            'latitude': 37.7750,
            'longitude': -122.4195,
            'speed_kmh': 65.5,
            'altitude': 15.0,
            'accuracy': 3.0,
            'heading': 180.0
        }
        response = self.client.post(gps_url, gps_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Add Emergency Event
        emergency_url = reverse('recording-add-emergency', args=[recording_id])
        emergency_data = {
            'latitude': 37.7751,
            'longitude': -122.4196,
            'speed_kmh': 70.0,
            'description': 'Crash impact suspected'
        }
        response = self.client.post(emergency_url, emergency_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Search recordings
        search_url = reverse('recording-search')
        response = self.client.get(f"{search_url}?q=Test&is_emergency=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Result should contain the emergency recording we updated
        self.assertEqual(len(response.data.get('results', response.data)), 1)

        # Export GPS
        export_url = reverse('recording-export-gps', args=[recording_id])
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['latitude']), 37.7750)
