from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    distance_radius = models.IntegerField(default=25, null=True, blank=True)
    about_me = models.TextField(null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    notify_events = models.BooleanField(default=True)
    notify_recommendations = models.BooleanField(default=True)
    notify_looking_for = models.BooleanField(default=True)
    is_subscribed = models.BooleanField(default=False)
    subscription_expiry = models.DateTimeField(null=True, blank=True)
    current_plan = models.ForeignKey('custom_admin.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)

    def check_subscription(self):
        from django.utils import timezone
        if self.is_subscribed and self.subscription_expiry and self.subscription_expiry < timezone.now():
            self.is_subscribed = False
            self.save(update_fields=['is_subscribed'])
        return self.is_subscribed



class OTP(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=5)


class Friendship(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friendships')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friendships')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sender', 'receiver'], name='unique_friendship_request')
        ]

    def __str__(self):
        return f"{self.sender.email} -> {self.receiver.email} ({self.status})"