from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils.crypto import get_random_string

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
import random
from django.core.mail import send_mail
from .models import User, OTP, Friendship
from django.db.models import Q

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    RegisterSerializer,
    RegisterSuccessResponseSerializer,
    RegisterErrorResponseSerializer,
    LoginSerializer,
    LoginSuccessResponseSerializer,
    LoginErrorResponseSerializer,
    ChangePasswordSerializer,
    ProfileSerializer,
    ProfileResponseSerializer,
    ProfileUpdateResponseSerializer,
    ForgotPasswordSerializer,
    VerifyOTPSerializer,
    ResetPasswordSerializer,
    NearbyUserSerializer,
    FriendUserSerializer,
    FriendRequestSerializer,
    MyItemsResponseSerializer,
    GoogleLoginSerializer,
)
from .firebase_auth import verify_firebase_token
import requests
from django.core.files.base import ContentFile



class RegisterView(APIView):

    @swagger_auto_schema(
        operation_summary="Register User",
        operation_description="Create a new account and return JWT access and refresh tokens.",
        request_body=RegisterSerializer,
        responses={
            201: RegisterSuccessResponseSerializer,
            400: RegisterErrorResponseSerializer,
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "full_name": user.first_name,
                    "email": user.email,
                }
            },
            status=status.HTTP_201_CREATED
        )



class LoginView(APIView):

    @swagger_auto_schema(
        operation_summary="Login User",
        operation_description="Login with email and password and receive JWT tokens.",
        request_body=LoginSerializer,
        responses={
            200: LoginSuccessResponseSerializer,
            400: LoginErrorResponseSerializer,
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "full_name": user.first_name,
                    "email": user.email,
                },
            },
            status=status.HTTP_200_OK,
        )



class GoogleLoginView(APIView):

    @swagger_auto_schema(
        operation_summary="Google / Firebase Login",
        operation_description="Authenticate user via Google ID Token from Firebase.",
        request_body=GoogleLoginSerializer,
        responses={
            200: LoginSuccessResponseSerializer,
            201: LoginSuccessResponseSerializer,
            400: LoginErrorResponseSerializer,
        }
    )
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        id_token = serializer.validated_data["id_token"]

        try:
            decoded_token = verify_firebase_token(id_token)
        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "errors": {"id_token": e.detail}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = decoded_token.get("email")
        name = decoded_token.get("name", "")
        picture_url = decoded_token.get("picture", "")

        if not email:
            return Response(
                {
                    "success": False,
                    "errors": {"id_token": ["Email address is required in the Google token."]}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email).first()
        created = False

        if not user:
            # Register new user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=get_random_string(32),
                first_name=name
            )
            created = True

            # Download profile picture
            if picture_url:
                try:
                    response = requests.get(picture_url, timeout=10)
                    if response.status_code == 200:
                        filename = f"google_profile_{user.id}.jpg"
                        user.profile_photo.save(filename, ContentFile(response.content), save=True)
                except Exception:
                    pass

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Registration and login successful." if created else "Login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "full_name": user.first_name,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )




        
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change Password",
        operation_description="Change password for authenticated user.",
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "errors": openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            )
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Password changed successfully"
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Get User Profile",
        operation_description="Get profile details of the authenticated user.",
        responses={
            200: ProfileResponseSerializer
        }
    )
    def get(self, request):
        serializer = ProfileSerializer(request.user, context={'request': request})
        return Response(
            {
                "success": True,
                "profile": serializer.data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        operation_summary="Update User Profile",
        operation_description="Replace profile details (including uploading a photo) of the authenticated user.",
        request_body=ProfileSerializer,
        consumes=['application/json', 'multipart/form-data'],
        responses={
            200: ProfileUpdateResponseSerializer,
            400: "Bad Request"
        }
    )
    def put(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=False,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Profile updated successfully.",
                    "profile": serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_summary="Partially Update User Profile",
        operation_description="Partially update profile details (including uploading a photo) of the authenticated user.",
        request_body=ProfileSerializer,
        consumes=['application/json', 'multipart/form-data'],
        responses={
            200: ProfileUpdateResponseSerializer,
            400: "Bad Request"
        }
    )
    def patch(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Profile updated successfully.",
                    "profile": serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class ForgotPasswordView(APIView):
    @swagger_auto_schema(
        operation_summary="Forgot Password - Send OTP",
        operation_description="Send a 4-digit OTP to the user's email for password recovery.",
        request_body=ForgotPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad Request")
        }
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        
        # Delete any existing OTP codes for this email
        OTP.objects.filter(email=email).delete()

        # Generate a random 4-digit OTP code
        otp_code = f"{random.randint(1000, 9999)}"

        # Save to DB
        OTP.objects.create(email=email, code=otp_code)

        # Send email (console printout)
        send_mail(
            subject="Password Reset OTP",
            message=f"Your password reset verification code is: {otp_code}",
            from_email="no-reply@example.com",
            recipient_list=[email],
            fail_silently=False,
        )

        # Also print to terminal explicitly so it is very obvious to the developer
        print(f"\n========================================\n[OTP EMAIL SENT TO {email}]\nOTP CODE: {otp_code}\n========================================\n")

        return Response(
            {
                "success": True,
                "message": "OTP has been sent to your email address."
            },
            status=status.HTTP_200_OK
        )


class VerifyOTPView(APIView):
    @swagger_auto_schema(
        operation_summary="Verify OTP",
        operation_description="Verify the 4-digit OTP sent to the user's email.",
        request_body=VerifyOTPSerializer,
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad Request")
        }
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_record = serializer.validated_data['otp_record']
        otp_record.is_verified = True
        otp_record.save()

        return Response(
            {
                "success": True,
                "message": "OTP has been verified successfully. You can now reset your password."
            },
            status=status.HTTP_200_OK
        )


class ResetPasswordView(APIView):
    @swagger_auto_schema(
        operation_summary="Reset Password using OTP",
        operation_description="Reset the password using verified email and new credentials.",
        request_body=ResetPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad Request")
        }
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        otp_record = serializer.validated_data['otp_record']

        # Find user and update password
        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()

        # Delete all OTP records for this email to prevent reuse
        OTP.objects.filter(email=email).delete()

        return Response(
            {
                "success": True,
                "message": "Password has been reset successfully. You can now login with your new password."
            },
            status=status.HTTP_200_OK
        )


class NearbyUsersView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Nearby Users",
        operation_description="Retrieve other users within a specified distance radius (in kilometers) from the user's location or custom location query parameters. Optionally filter by name.",
        manual_parameters=[
            openapi.Parameter('latitude', openapi.IN_QUERY, description="Custom latitude to search from", type=openapi.TYPE_NUMBER),
            openapi.Parameter('longitude', openapi.IN_QUERY, description="Custom longitude to search from", type=openapi.TYPE_NUMBER),
            openapi.Parameter('distance', openapi.IN_QUERY, description="Radius distance in kilometers (defaults to user's distance_radius setting, or 25 if not set)", type=openapi.TYPE_NUMBER),
            openapi.Parameter('search', openapi.IN_QUERY, description="Filter users by full name (case-insensitive)", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="List of nearby users sorted by distance ascending",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "base_location": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "latitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                                "longitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                            }
                        ),
                        "radius_km": openapi.Schema(type=openapi.TYPE_NUMBER),
                        "results": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "full_name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "email": openapi.Schema(type=openapi.TYPE_STRING),
                                    "profile_photo": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
                                    "latitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                                    "longitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                                    "distance_km": openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Bad Request - location coordinates not set or invalid parameters",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def get(self, request):
        user = request.user
        
        # Get query parameters
        lat_param = request.query_params.get('latitude')
        lon_param = request.query_params.get('longitude')
        dist_param = request.query_params.get('distance')
        search_param = request.query_params.get('search')

        # Determine base location
        if lat_param is not None and lon_param is not None:
            try:
                base_lat = float(lat_param)
                base_lon = float(lon_param)
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid coordinates provided in query parameters."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            if user.latitude is None or user.longitude is None:
                return Response(
                    {
                        "success": False,
                        "message": "User location coordinates (latitude and longitude) are not set in their profile. Please provide latitude and longitude query parameters or update your profile."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            base_lat = float(user.latitude)
            base_lon = float(user.longitude)

        # Determine search radius
        if dist_param is not None:
            try:
                radius = float(dist_param)
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid distance provided in query parameters."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            radius = float(user.distance_radius) if user.distance_radius is not None else 25.0

        # Fetch other users who have coordinates set
        other_users = User.objects.exclude(id=user.id).filter(latitude__isnull=False, longitude__isnull=False)

        # Filter by full name if search parameter is provided
        if search_param:
            other_users = other_users.filter(first_name__icontains=search_param)

        from events.views import haversine_distance

        nearby_users = []
        for other_user in other_users:
            dist = haversine_distance(base_lat, base_lon, other_user.latitude, other_user.longitude)
            if dist <= radius:
                other_user.distance_km = round(dist, 2)
                nearby_users.append(other_user)

        # Sort by distance
        nearby_users.sort(key=lambda u: u.distance_km)

        serializer = NearbyUserSerializer(nearby_users, many=True, context={'request': request})
        return Response(
            {
                "success": True,
                "base_location": {
                    "latitude": base_lat,
                    "longitude": base_lon
                },
                "radius_km": radius,
                "results": serializer.data
            },
            status=status.HTTP_200_OK
        )


class SendFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Send Friend Request",
        operation_description="Send a friend request to another user by providing their user ID.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['receiver_id'],
            properties={
                'receiver_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the user to send request to")
            }
        ),
        responses={
            201: openapi.Response(description="Friend request sent successfully"),
            200: openapi.Response(description="Friend request accepted automatically (mutual request)"),
            400: openapi.Response(description="Bad Request - self-request, duplicate request, or already friends"),
            404: openapi.Response(description="Recipient not found")
        }
    )
    def post(self, request):
        receiver_id = request.data.get('receiver_id')
        if not receiver_id:
            return Response({"success": False, "message": "receiver_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receiver_id_int = int(receiver_id)
        except ValueError:
            return Response({"success": False, "message": "Invalid receiver_id."}, status=status.HTTP_400_BAD_REQUEST)

        if receiver_id_int == request.user.id:
            return Response({"success": False, "message": "You cannot send a friend request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receiver = User.objects.get(id=receiver_id_int)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if there is an existing friendship or pending request in either direction
        existing = Friendship.objects.filter(
            Q(sender=request.user, receiver=receiver) |
            Q(sender=receiver, receiver=request.user)
        ).first()

        if existing:
            if existing.status == 'accepted':
                return Response({"success": False, "message": "You are already friends with this user."}, status=status.HTTP_400_BAD_REQUEST)
            elif existing.sender == request.user:
                return Response({"success": False, "message": "Friend request already sent."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # A pending request exists from receiver to request.user. Auto-accept it.
                existing.status = 'accepted'
                existing.save()
                return Response({"success": True, "message": "Friend request accepted automatically as they had already sent you a request.", "status": "accepted"}, status=status.HTTP_200_OK)

        Friendship.objects.create(sender=request.user, receiver=receiver, status='pending')
        return Response({"success": True, "message": "Friend request sent successfully.", "status": "pending"}, status=status.HTTP_201_CREATED)


class IncomingFriendRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Incoming Friend Requests",
        operation_description="Retrieve a list of pending incoming friend requests.",
        responses={
            200: openapi.Response(
                description="List of incoming friend requests",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "requests": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "sender": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                            "full_name": openapi.Schema(type=openapi.TYPE_STRING),
                                            "email": openapi.Schema(type=openapi.TYPE_STRING),
                                            "profile_photo": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
                                            "latitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                                            "longitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                                        }
                                    ),
                                    "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                }
                            )
                        ),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            )
        }
    )
    def get(self, request):
        requests = Friendship.objects.filter(receiver=request.user, status='pending').order_by('-created_at')
        serializer = FriendRequestSerializer(requests, many=True, context={'request': request})
        return Response({
            "success": True,
            "count": requests.count(),
            "requests": serializer.data
        }, status=status.HTTP_200_OK)


class AcceptFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Accept Friend Request",
        operation_description="Accept a pending incoming friend request by request ID.",
        responses={
            200: openapi.Response(description="Friend request accepted"),
            404: openapi.Response(description="Request not found")
        }
    )
    def post(self, request, request_id):
        try:
            friend_request = Friendship.objects.get(id=request_id, receiver=request.user, status='pending')
        except Friendship.DoesNotExist:
            return Response({"success": False, "message": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)

        friend_request.status = 'accepted'
        friend_request.save()
        return Response({"success": True, "message": "Friend request accepted. You are now friends!"}, status=status.HTTP_200_OK)


class RejectFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Reject Friend Request",
        operation_description="Reject or cancel a pending friend request by request ID.",
        responses={
            200: openapi.Response(description="Friend request deleted successfully"),
            404: openapi.Response(description="Request not found")
        }
    )
    def post(self, request, request_id):
        try:
            # Allow receiver to reject, or sender to cancel their pending request
            friend_request = Friendship.objects.get(
                Q(id=request_id, status='pending') &
                (Q(receiver=request.user) | Q(sender=request.user))
            )
        except Friendship.DoesNotExist:
            return Response({"success": False, "message": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)

        friend_request.delete()
        return Response({"success": True, "message": "Friend request deleted successfully."}, status=status.HTTP_200_OK)


class FriendsListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Friends List",
        operation_description="Retrieve a list of the user's friends.",
        responses={
            200: openapi.Response(
                description="List of friends",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "friends": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "full_name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "email": openapi.Schema(type=openapi.TYPE_STRING),
                                    "profile_photo": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
                                    "latitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                                    "longitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        ),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            )
        }
    )
    def get(self, request):
        friendships = Friendship.objects.filter(
            Q(status='accepted') &
            (Q(sender=request.user) | Q(receiver=request.user))
        )

        friends = []
        for f in friendships:
            if f.sender == request.user:
                friends.append(f.receiver)
            else:
                friends.append(f.sender)

        serializer = FriendUserSerializer(friends, many=True, context={'request': request})
        return Response({
            "success": True,
            "count": len(friends),
            "friends": serializer.data
        }, status=status.HTTP_200_OK)


class RemoveFriendView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Remove Friend",
        operation_description="Remove a user from your friends list.",
        responses={
            200: openapi.Response(description="Friend removed successfully"),
            404: openapi.Response(description="Friendship not found")
        }
    )
    def delete(self, request, friend_id):
        try:
            friendship = Friendship.objects.get(
                Q(status='accepted') &
                (
                    Q(sender=request.user, receiver_id=friend_id) |
                    Q(sender_id=friend_id, receiver=request.user)
                )
            )
        except Friendship.DoesNotExist:
            return Response({"success": False, "message": "Friendship not found."}, status=status.HTTP_404_NOT_FOUND)

        friendship.delete()
        return Response({"success": True, "message": "Friend removed successfully."}, status=status.HTTP_200_OK)


class PlanListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Subscription Plans",
        operation_description="Get the list of all active subscription plans.",
        tags=['Payment'],
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "plans": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT))
                    }
                )
            )
        }
    )
    def get(self, request):
        from custom_admin.models import SubscriptionPlan
        from custom_admin.serializers import SubscriptionPlanSerializer
        
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response({
            "success": True,
            "count": len(plans),
            "plans": serializer.data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create Stripe Checkout Session",
        operation_description="Create a Stripe Checkout Session for a specific subscription plan to buy a package.",
        tags=['Payment'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["plan_id"],
            properties={
                "plan_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the plan to buy"),
                "success_url": openapi.Schema(type=openapi.TYPE_STRING, description="Optional custom success URL (can include {CHECKOUT_SESSION_ID})"),
                "cancel_url": openapi.Schema(type=openapi.TYPE_STRING, description="Optional custom cancel URL")
            }
        ),
        responses={
            200: openapi.Response(
                description="Checkout session created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "checkout_url": openapi.Schema(type=openapi.TYPE_STRING),
                        "session_id": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Invalid plan or request data",
            404: "Plan not found"
        }
    )
    def post(self, request):
        import stripe
        from django.conf import settings
        from custom_admin.models import SubscriptionPlan

        stripe.api_key = settings.STRIPE_SECRET_KEY

        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({"success": False, "message": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"success": False, "message": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')

        if not success_url:
            success_url = request.build_absolute_uri('/api/plans/') + 'verify/?session_id={CHECKOUT_SESSION_ID}'
        if not cancel_url:
            cancel_url = request.build_absolute_uri('/api/plans/')

        try:
            amount_in_cents = int(plan.price * 100)

            if plan.discount_offer > 0:
                discount_amount = (amount_in_cents * plan.discount_offer) // 100
                amount_in_cents = max(0, amount_in_cents - discount_amount)

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'aud',
                            'product_data': {
                                'name': plan.name,
                                'description': f"Subscription Plan - {plan.get_billing_cycle_display()}",
                            },
                            'unit_amount': amount_in_cents,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': request.user.id,
                    'plan_id': plan.id,
                }
            )

            return Response({
                "success": True,
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PlanVerifyView(APIView):
    from rest_framework.permissions import AllowAny
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify Stripe Checkout Session",
        operation_description="Verify checkout session payment and activate subscription if successful.",
        tags=['Payment'],
        manual_parameters=[
            openapi.Parameter('session_id', openapi.IN_QUERY, description="Stripe Checkout Session ID", type=openapi.TYPE_STRING, required=True)
        ],
        responses={
            200: openapi.Response(
                description="Subscription verified and updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_subscribed": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "subscription_expiry": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Invalid session_id or verification failed"
        }
    )
    def get(self, request):
        import stripe
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        from custom_admin.models import SubscriptionPlan
        from accounts.models import User

        stripe.api_key = settings.STRIPE_SECRET_KEY
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({"success": False, "message": "session_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status != 'paid':
                return Response({"success": False, "message": "Session has not been paid yet."}, status=status.HTTP_400_BAD_REQUEST)

            metadata = session.metadata
            user_id = metadata.get('user_id')
            plan_id = metadata.get('plan_id')

            if not user_id or not plan_id:
                return Response({"success": False, "message": "Invalid session metadata."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(id=user_id)
                plan = SubscriptionPlan.objects.get(id=plan_id)
            except (User.DoesNotExist, SubscriptionPlan.DoesNotExist):
                return Response({"success": False, "message": "User or Plan from metadata not found."}, status=status.HTTP_400_BAD_REQUEST)

            if plan.billing_cycle == 'monthly':
                duration = timedelta(days=30)
            elif plan.billing_cycle == 'yearly':
                duration = timedelta(days=365)
            else:
                duration = timedelta(days=30)

            now = timezone.now()
            if user.subscription_expiry and user.subscription_expiry > now:
                start_date = user.subscription_expiry
            else:
                start_date = now

            new_expiry = start_date + duration

            user.is_subscribed = True
            user.subscription_expiry = new_expiry
            user.current_plan = plan
            user.save()

            # Print payment details directly to Django terminal
            print("\n" + "=" * 60)
            print("STRIPE PAYMENT VERIFICATION SUCCESSFUL")
            print(f"Session ID:         {session_id}")
            print(f"User:               {user.username} (ID: {user.id}, Email: {user.email})")
            print(f"Plan:               {plan.name} (ID: {plan.id})")
            print(f"Amount Paid:        AU$ {plan.price}")
            print(f"Billing Cycle:      {plan.get_billing_cycle_display()}")
            print(f"New Expiry Date:    {new_expiry}")
            print("=" * 60 + "\n")

            return Response({
                "success": True,
                "message": "Subscription successfully activated/extended.",
                "is_subscribed": user.is_subscribed,
                "subscription_expiry": user.subscription_expiry
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StripeWebhookView(APIView):
    from rest_framework.permissions import AllowAny
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Stripe Webhook Handler",
        operation_description="Handles webhook events sent by Stripe. Processes checkout.session.completed to activate subscriptions.",
        tags=['Payment'],
        responses={
            200: "Webhook handled successfully",
            400: "Signature verification failed or invalid payload"
        }
    )
    def post(self, request):
        import stripe
        import json
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        from custom_admin.models import SubscriptionPlan
        from accounts.models import User

        stripe.api_key = settings.STRIPE_SECRET_KEY
        payload = request.body
        sig_header = request.headers.get('STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        event = None

        try:
            if endpoint_secret and endpoint_secret != 'whsec_test_secret':
                event = stripe.Webhook.construct_event(
                    payload, sig_header, endpoint_secret
                )
            else:
                event_dict = json.loads(payload)
                event = stripe.Event.construct_from(event_dict, stripe.api_key)
        except ValueError as e:
            return Response({"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            if session.get('payment_status') == 'paid':
                metadata = session.get('metadata', {})
                user_id = metadata.get('user_id')
                plan_id = metadata.get('plan_id')
                plan_type = metadata.get('plan_type')

                if user_id and plan_id:
                    if plan_type == 'deal':
                        from deal.models import DealPlan
                        try:
                            user = User.objects.get(id=user_id)
                            plan = DealPlan.objects.get(id=plan_id)

                            if plan.billing_cycle == 'monthly':
                                duration = timedelta(days=30)
                            elif plan.billing_cycle == 'yearly':
                                duration = timedelta(days=365)
                            else:
                                duration = timedelta(days=30)

                            now = timezone.now()
                            if user.deal_subscription_expiry and user.deal_subscription_expiry > now:
                                start_date = user.deal_subscription_expiry
                            else:
                                start_date = now

                            new_expiry = start_date + duration

                            user.is_deal_subscribed = True
                            user.deal_subscription_expiry = new_expiry
                            user.current_deal_plan = plan
                            user.save()

                            # Print deal payment details directly to Django terminal
                            print("\n" + "=" * 60)
                            print("STRIPE WEBHOOK DEAL PLAN PAYMENT RECEIVED")
                            print(f"Session ID:         {session.get('id')}")
                            print(f"User:               {user.username} (ID: {user.id}, Email: {user.email})")
                            print(f"Deal Plan:          {plan.name} (ID: {plan.id})")
                            print(f"Amount Paid:        AU$ {plan.price}")
                            print(f"Billing Cycle:      {plan.get_billing_cycle_display()}")
                            print(f"New Expiry Date:    {new_expiry}")
                            print("=" * 60 + "\n")
                        except (User.DoesNotExist, DealPlan.DoesNotExist):
                            pass
                    else:
                        try:
                            user = User.objects.get(id=user_id)
                            plan = SubscriptionPlan.objects.get(id=plan_id)

                            if plan.billing_cycle == 'monthly':
                                duration = timedelta(days=30)
                            elif plan.billing_cycle == 'yearly':
                                duration = timedelta(days=365)
                            else:
                                duration = timedelta(days=30)

                            now = timezone.now()
                            if user.subscription_expiry and user.subscription_expiry > now:
                                start_date = user.subscription_expiry
                            else:
                                start_date = now

                            new_expiry = start_date + duration

                            user.is_subscribed = True
                            user.subscription_expiry = new_expiry
                            user.current_plan = plan
                            user.save()

                            # Print payment details directly to Django terminal
                            print("\n" + "=" * 60)
                            print("STRIPE WEBHOOK PAYMENT RECEIVED")
                            print(f"Session ID:         {session.get('id')}")
                            print(f"User:               {user.username} (ID: {user.id}, Email: {user.email})")
                            print(f"Plan:               {plan.name} (ID: {plan.id})")
                            print(f"Amount Paid:        AU$ {plan.price}")
                            print(f"Billing Cycle:      {plan.get_billing_cycle_display()}")
                            print(f"New Expiry Date:    {new_expiry}")
                            print("=" * 60 + "\n")
                        except (User.DoesNotExist, SubscriptionPlan.DoesNotExist):
                            pass

        return Response({"success": True}, status=status.HTTP_200_OK)


class MySubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Current User's Subscription Details",
        operation_description="Retrieve active subscription plan details and expiry date for the authenticated user.",
        tags=['Payment'],
        responses={
            200: openapi.Response(
                description="User subscription details retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "is_subscribed": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "subscription_expiry": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True),
                        "current_plan": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            nullable=True,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "name": openapi.Schema(type=openapi.TYPE_STRING),
                                "price": openapi.Schema(type=openapi.TYPE_STRING),
                                "billing_cycle": openapi.Schema(type=openapi.TYPE_STRING),
                                "discount_offer": openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        from custom_admin.serializers import SubscriptionPlanSerializer
        user = request.user
        
        user.check_subscription()
        
        plan_data = None
        if user.current_plan:
            plan_data = SubscriptionPlanSerializer(user.current_plan).data
            
        return Response({
            "success": True,
            "is_subscribed": user.is_subscribed,
            "subscription_expiry": user.subscription_expiry,
            "current_plan": plan_data
        }, status=status.HTTP_200_OK)



class MyItemsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get User's Created Items",
        operation_description="Retrieve all alerts, events, recommendations, and looking-for posts created by the authenticated user in a single request.",
        responses={
            200: MyItemsResponseSerializer
        }
    )
    def get(self, request):
        from alert.models import Alert
        from alert.serializers import AlertSerializer
        from events.models import Event
        from events.serializers import EventSerializer
        from recommendations.models import Recommendation
        from recommendations.serializers import RecommendationSerializer
        from looking_for.models import LookingFor
        from looking_for.serializers import LookingForSerializer

        user = request.user

        alerts = Alert.objects.filter(creator=user)
        events = Event.objects.filter(creator=user)
        recommendations = Recommendation.objects.filter(creator=user)
        looking_for = LookingFor.objects.filter(creator=user)

        context = {'request': request}

        alerts_data = AlertSerializer(alerts, many=True, context=context).data
        events_data = EventSerializer(events, many=True, context=context).data
        recommendations_data = RecommendationSerializer(recommendations, many=True, context=context).data
        looking_for_data = LookingForSerializer(looking_for, many=True, context=context).data

        combined_items = list(alerts_data) + list(events_data) + list(recommendations_data) + list(looking_for_data)

        from django.utils.dateparse import parse_datetime
        from django.utils import timezone

        combined_items.sort(
            key=lambda x: parse_datetime(x.get('created_at')) if x.get('created_at') else timezone.now(),
            reverse=True
        )

        return Response({
            "success": True,
            "items": combined_items
        }, status=status.HTTP_200_OK)