from django.db import models
from django.conf import settings

class Event(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_events')
    event_banner = models.ImageField(upload_to='event_banners/', null=True, blank=True)
    name = models.CharField(max_length=255)
    date_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    description = models.TextField(blank=True, default='')
    is_ticketed = models.BooleanField(default=False)
    require_rsvp = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
