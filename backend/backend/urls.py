from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="index.html"), name='home'),
    path('domain-selection/', TemplateView.as_view(template_name="domain_select.html"), name='domain_selection'),
    path('api/v1/', include('tasks.urls')),
]
