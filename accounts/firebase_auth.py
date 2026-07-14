import os
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from rest_framework.exceptions import ValidationError

def initialize_firebase():
    try:
        # Check if already initialized
        firebase_admin.get_app()
    except ValueError:
        # Not initialized yet
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            # Fallback to default credentials (e.g. standard GCP env or credentials file)
            firebase_admin.initialize_app()

def verify_firebase_token(id_token):
    initialize_firebase()
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise ValidationError("Firebase ID token has expired.")
    except auth.InvalidIdTokenError:
        raise ValidationError("Invalid Firebase ID token.")
    except Exception as e:
        raise ValidationError(f"Firebase token verification failed: {str(e)}")
