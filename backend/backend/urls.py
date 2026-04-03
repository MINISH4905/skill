from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from tasks.views import api_health_check
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Main Frontend Entry Point
    path('', TemplateView.as_view(template_name="index.html"), name='home'),
    
    path('health/', api_health_check, name='direct_health_check'),
    path('api/v1/', include('tasks.urls')),
    
    # Documentation endpoints
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
