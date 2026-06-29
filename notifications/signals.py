from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from events.models import Event
from recommendations.models import Recommendation
from looking_for.models import LookingFor
from accounts.models import Friendship
from events.views import haversine_distance
from .models import Notification
from .serializers import NotificationSerializer

User = get_user_model()
channel_layer = get_channel_layer()

def notify_matching_users(post, post_type):
    creator = post.creator
    
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

    # 2. Get list of users to potentially notify based on their notification preferences
    filter_kwargs = {
        'is_active': True,
    }
    if post_type == 'event':
        filter_kwargs['notify_events'] = True
    elif post_type == 'recommendation':
        filter_kwargs['notify_recommendations'] = True
    elif post_type == 'looking_for':
        filter_kwargs['notify_looking_for'] = True
        
    candidates = User.objects.filter(**filter_kwargs).exclude(id=creator.id)
    
    # 3. Filter candidates by distance and friendship
    for user in candidates:
        if user.latitude is None or user.longitude is None:
            continue
            
        radius = user.distance_radius if user.distance_radius is not None else 25
        is_friend = user.id in friend_ids
        dist = None
        
        if post.latitude is not None and post.longitude is not None:
            dist = haversine_distance(user.latitude, user.longitude, post.latitude, post.longitude)
            
        if is_friend or (dist is not None and dist <= radius):
            # Create the Notification database record
            title = ""
            message = ""
            event_obj = None
            rec_obj = None
            lf_obj = None
            
            creator_name = creator.first_name if creator.first_name else creator.email
            
            if post_type == 'event':
                title = "New Upcoming Event"
                message = f"{creator_name} posted a new event: {post.name}."
                event_obj = post
            elif post_type == 'recommendation':
                title = "New Recommendation"
                message = f"{creator_name} posted a recommendation in {post.category}."
                rec_obj = post
            elif post_type == 'looking_for':
                title = "New Looking For Request"
                message = f"{creator_name} is looking for {post.category}."
                lf_obj = post
                
            notification = Notification.objects.create(
                user=user,
                notification_type=post_type,
                title=title,
                message=message,
                event=event_obj,
                recommendation=rec_obj,
                looking_for=lf_obj
            )
            
            # Send real-time notification via Channels if layer is active
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

@receiver(post_save, sender=Event)
def event_post_save(sender, instance, created, **kwargs):
    if created:
        notify_matching_users(instance, 'event')

@receiver(post_save, sender=Recommendation)
def recommendation_post_save(sender, instance, created, **kwargs):
    if created:
        notify_matching_users(instance, 'recommendation')

@receiver(post_save, sender=LookingFor)
def looking_for_post_save(sender, instance, created, **kwargs):
    if created:
        notify_matching_users(instance, 'looking_for')
