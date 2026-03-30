from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, default='')
    avatar_color = models.CharField(max_length=7, default='#6C63FF')

    def __str__(self):
        return self.username