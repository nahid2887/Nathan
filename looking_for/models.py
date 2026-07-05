from django.db import models
from django.conf import settings

class LookingFor(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='looking_for_requests')
    category = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255, null=True, blank=True)
    details = models.TextField()
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
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

class LookingForLike(models.Model):
    looking_for = models.ForeignKey(LookingFor, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='looking_for_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['looking_for', 'user'], name='unique_looking_for_like')
        ]

    def __str__(self):
        return f"{self.user.email} likes LookingFor {self.looking_for.id}"

class LookingForComment(models.Model):
    looking_for = models.ForeignKey(LookingFor, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='looking_for_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} on LookingFor {self.looking_for.id}: {self.content[:30]}"

class LookingForShare(models.Model):
    looking_for = models.ForeignKey(LookingFor, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='looking_for_shares')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} shared LookingFor {self.looking_for.id}"


