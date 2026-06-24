from django.db import models
from django.conf import settings

class LookingFor(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='looking_for_requests')
    category = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255, null=True, blank=True)
    details = models.TextField()
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.creator.email} - {self.category}"

class LookingForPhoto(models.Model):
    looking_for = models.ForeignKey(LookingFor, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='looking_for_photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for Request ID {self.looking_for.id}"

