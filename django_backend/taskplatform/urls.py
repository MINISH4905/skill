"""
URL configuration for taskplatform project.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse  # 👈 ADD THIS


# 👇 Home view (simple test view)
def home(request):
    return HttpResponse("Backend Running Successfully 🚀")


urlpatterns = [
    path('', home, name='home'),  # 👈 ADD THIS LINE

    path('admin/', admin.site.urls),

    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('domains/', include(('domains.urls', 'domains'), namespace='domains')),
    path('tasks/', include(('tasks.urls', 'tasks'), namespace='tasks')),
    path('progress/', include(('progress.urls', 'progress'), namespace='progress')),
]