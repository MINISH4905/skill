from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, default='')
    avatar_color = models.CharField(max_length=7, default='#6C63FF')

    def get_selected_domains(self):
        return self.domain_preferences.filter(is_selected=True)

    def __str__(self):
        return self.username


class UserDomainPreference(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='domain_preferences'
    )
    domain = models.CharField(max_length=100)  # temporary (later FK)
    is_selected = models.BooleanField(default=True)
    selected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.domain}"