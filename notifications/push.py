from firebase_admin import messaging
from accounts.firebase_auth import initialize_firebase

def send_push_notification(user, title, body, data=None):
    fcm_token = getattr(user, 'fcm_token', None)
    if not fcm_token:
        return None

    try:
        initialize_firebase()
        
        # Ensure all data values are strings for FCM payload
        string_data = {}
        if data:
            for k, v in data.items():
                string_data[str(k)] = str(v)
                
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=string_data,
            token=fcm_token,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        print(f"FCM push notification error: {str(e)}")
        return None
