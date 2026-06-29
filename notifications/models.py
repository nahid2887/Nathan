from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('event', 'Event'),
        ('recommendation', 'Recommendation'),
        ('looking_for', 'Looking For'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, null=True, blank=True)
    recommendation = models.ForeignKey('recommendations.Recommendation', on_delete=models.CASCADE, null=True, blank=True)
    looking_for = models.ForeignKey('looking_for.LookingFor', on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.notification_type} - {self.title}"
