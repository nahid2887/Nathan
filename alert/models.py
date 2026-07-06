from django.db import models
from django.conf import settings

class Alert(models.Model):
    TYPE_CHOICES = [
        ('alert', 'Alerts'),
        ('missing', 'Missing'),
        ('emergency', 'Emergency'),
    ]

    LEVEL_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
    ]

    PRIVACY_CHOICES = [
        ('anyone', 'Anyone in HoodLink'),
        ('friends', 'Friends'),
        ('only_me', 'Only me'),
    ]

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alerts')
    title = models.CharField(max_length=255, default='', blank=True)
    content = models.TextField(max_length=500, blank=True, default='')
    location_name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=22, decimal_places=16)
    longitude = models.DecimalField(max_digits=22, decimal_places=16)
    alert_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='alert')
    alert_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='medium')
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='anyone')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_alert_type_display()} ({self.get_alert_level_display()}) at {self.location_name}"

    class Meta:
        ordering = ['-created_at']
