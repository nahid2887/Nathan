import os
import jwt
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from rest_framework.exceptions import ValidationError
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

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

def verify_firebase_token(token):
    try:
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        raise ValidationError("Invalid token format.")

    iss = unverified_claims.get("iss", "")

    if iss == "https://accounts.google.com":
        try:
            decoded_token = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request()
            )
            return decoded_token
        except Exception as e:
            raise ValidationError(f"Google ID token verification failed: {str(e)}")
    else:
        initialize_firebase()
        try:
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        except auth.ExpiredIdTokenError:
            raise ValidationError("Firebase ID token has expired.")
        except auth.InvalidIdTokenError:
            raise ValidationError("Invalid Firebase ID token.")
        except Exception as e:
            raise ValidationError(f"Firebase token verification failed: {str(e)}")

