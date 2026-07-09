from django.db import models
from django.conf import settings

class ProductAd(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='product_ads'
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    description = models.TextField()
    phone_number = models.CharField(max_length=50)
    email_address = models.EmailField()
    website = models.URLField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    business_hours = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.category})"


class ProductAdPhoto(models.Model):
    product_ad = models.ForeignKey(
        ProductAd, 
        on_delete=models.CASCADE, 
        related_name='photos'
    )
    image = models.ImageField(upload_to='product_ad_photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for ProductAd ID {self.product_ad.id}"
