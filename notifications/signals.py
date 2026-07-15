from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from looking_for.models import LookingForLike, LookingForComment
from recommendations.models import RecommendationLike, RecommendationComment
from alert.models import Alert
from accounts.models import Friendship
from events.views import haversine_distance
from .models import Notification
from .serializers import NotificationSerializer
from .push import send_push_notification

User = get_user_model()
channel_layer = get_channel_layer()

def create_and_send_notification(user, notification_type, title, message, event=None, recommendation=None, looking_for=None, alert=None):
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        event=event,
        recommendation=recommendation,
        looking_for=looking_for,
        alert=alert
    )
    
    # 1. Send Firebase Push Notification
    push_data = {
        "notification_id": str(notification.id),
        "type": notification_type,
    }
    if event:
        push_data["event_id"] = str(event.id)
    if recommendation:
        push_data["recommendation_id"] = str(recommendation.id)
    if looking_for:
        push_data["looking_for_id"] = str(looking_for.id)
    if alert:
        push_data["alert_id"] = str(alert.id)
        
    send_push_notification(user, title, message, data=push_data)

    # 2. Send real-time notification via Channels if layer is active
    if channel_layer:
        unread_count = Notification.objects.filter(user=user, is_read=False).count()
        data = NotificationSerializer(notification).data
        data['unread_count'] = unread_count
        
        try:
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "send_notification",
                    "data": data
                }
            )
        except Exception:
            # In test environment or environments without fully active layer setup
            pass
            
    return notification


@receiver(post_save, sender=LookingForLike)
def looking_for_like_save(sender, instance, created, **kwargs):
    if created:
        post = instance.looking_for
        recipient = post.creator
        sender_user = instance.user
        
        # Don't notify self
        if recipient != sender_user:
            sender_name = sender_user.first_name if sender_user.first_name else sender_user.email
            title = "New Like"
            message = f"{sender_name} liked your Looking For request."
            create_and_send_notification(
                user=recipient,
                notification_type='looking_for',
                title=title,
                message=message,
                looking_for=post
            )


@receiver(post_save, sender=LookingForComment)
def looking_for_comment_save(sender, instance, created, **kwargs):
    if created:
        post = instance.looking_for
        recipient = post.creator
        sender_user = instance.user
        
        # Don't notify self
        if recipient != sender_user:
            sender_name = sender_user.first_name if sender_user.first_name else sender_user.email
            title = "New Comment"
            message = f"{sender_name} commented on your Looking For request: {instance.content[:50]}"
            create_and_send_notification(
                user=recipient,
                notification_type='looking_for',
                title=title,
                message=message,
                looking_for=post
            )


@receiver(post_save, sender=RecommendationLike)
def recommendation_like_save(sender, instance, created, **kwargs):
    if created:
        post = instance.recommendation
        recipient = post.creator
        sender_user = instance.user
        
        # Don't notify self
        if recipient != sender_user:
            sender_name = sender_user.first_name if sender_user.first_name else sender_user.email
            title = "New Like"
            message = f"{sender_name} liked your Recommendation."
            create_and_send_notification(
                user=recipient,
                notification_type='recommendation',
                title=title,
                message=message,
                recommendation=post
            )


@receiver(post_save, sender=RecommendationComment)
def recommendation_comment_save(sender, instance, created, **kwargs):
    if created:
        post = instance.recommendation
        recipient = post.creator
        sender_user = instance.user
        
        # Don't notify self
        if recipient != sender_user:
            sender_name = sender_user.first_name if sender_user.first_name else sender_user.email
            title = "New Comment"
            message = f"{sender_name} commented on your Recommendation: {instance.content[:50]}"
            create_and_send_notification(
                user=recipient,
                notification_type='recommendation',
                title=title,
                message=message,
                recommendation=post
            )


@receiver(post_save, sender=Alert)
def alert_post_save(sender, instance, created, **kwargs):
    if created:
        creator = instance.creator
        privacy = instance.privacy
        
        if privacy == 'only_me':
            return
            
        # 1. Fetch friend IDs of the creator
        friendships = Friendship.objects.filter(
            Q(status='accepted') & (Q(sender=creator) | Q(receiver=creator))
        )
        friend_ids = set()
        for f in friendships:
            if f.sender == creator:
                friend_ids.add(f.receiver_id)
            else:
                friend_ids.add(f.sender_id)
                
        # 2. Query potential users to notify
        candidates = User.objects.filter(is_active=True).exclude(id=creator.id)
        
        for user in candidates:
            is_friend = user.id in friend_ids
            
            # Check privacy constraints
            if privacy == 'friends' and not is_friend:
                continue
                
            # If privacy is 'anyone', check radius proximity
            if privacy == 'anyone':
                # If they are a friend, they automatically match
                if not is_friend:
                    if user.latitude is None or user.longitude is None:
                        continue
                    if instance.latitude is None or instance.longitude is None:
                        continue
                        
                    radius = user.distance_radius if user.distance_radius is not None else 25
                    dist = haversine_distance(user.latitude, user.longitude, instance.latitude, instance.longitude)
                    if dist > radius:
                        continue
                        
            # If we reached here, notify the user
            creator_name = creator.first_name if creator.first_name else creator.email
            alert_type_display = instance.get_alert_type_display() if hasattr(instance, 'get_alert_type_display') else instance.alert_type
            
            title = f"New {alert_type_display}"
            message = f"{creator_name} posted a new {alert_type_display}: {instance.title or instance.content[:30]}."
            
            create_and_send_notification(
                user=user,
                notification_type='alert',
                title=title,
                message=message,
                alert=instance
            )
