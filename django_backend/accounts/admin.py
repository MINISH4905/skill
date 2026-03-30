from django.contrib import admin
from .models import CustomUser, UserDomainPreference

admin.site.register(CustomUser)
admin.site.register(UserDomainPreference)