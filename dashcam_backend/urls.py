from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/recordings/', include('api.urls')),
    
    # Frontend views
    path('', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('phone-app/', TemplateView.as_view(template_name='phone_app.html'), name='phone_app'),
    path('recording/<str:pk>/', TemplateView.as_view(template_name='recording_detail.html'), name='recording_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)