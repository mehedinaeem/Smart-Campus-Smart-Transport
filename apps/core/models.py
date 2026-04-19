from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_STUDENT = "student"
    ROLE_DRIVER = "driver"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_DRIVER, "Driver"),
        (ROLE_ADMIN, "Admin"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
