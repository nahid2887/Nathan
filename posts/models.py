from django.db import models
from django.conf import settings

class Post(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='posts'
    )
    title = models.CharField(max_length=255, blank=True, default='')
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', null=True, blank=True)
    photo = models.ImageField(upload_to='post_photos/', null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.creator.email} - {self.content[:30]}"


class PostPhoto(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='post_photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for Post ID {self.post.id}"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_post_like')
        ]

    def __str__(self):
        return f"{self.user.email} likes {self.post.id}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} on Post {self.post.id}: {self.content[:30]}"

