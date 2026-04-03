from django.urls import path
from . import views

urlpatterns = [
    # Health status
    path('health/', views.api_health_check, name='api_health_check'),
    
    # Task generation
    path('tasks/generate/', views.generate_task, name='generate_task'),
    path('tasks/next/', views.get_next_task, name='get_next_task'),
    path('tasks/<int:task_id>/', views.get_specific_task, name='get_specific_task'),
    path('tasks/submit/', views.submit_task, name='submit_task'),
    path('stats/', views.stats_view, name='stats'),
]
