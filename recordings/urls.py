from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import RecordingViewSet

router = DefaultRouter()
router.register(r'videos', RecordingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]