from django.db import models
from django.conf import settings

class Recommendation(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendations')
    category = models.CharField(max_length=255)
    rating = models.IntegerField(null=True, blank=True)  # rating between 1 and 5
    business_name = models.CharField(max_length=255, null=True, blank=True)
    details = models.TextField()
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.creator.email} - {self.category}"

class RecommendationPhoto(models.Model):
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='recommendation_photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for Rec ID {self.recommendation.id}"
