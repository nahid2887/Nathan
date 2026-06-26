from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
import random
from django.core.mail import send_mail
from .models import User, OTP

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
)


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
        operation_description="Retrieve other users within a specified distance radius (in kilometers) from the user's location or custom location query parameters.",
        manual_parameters=[
            openapi.Parameter('latitude', openapi.IN_QUERY, description="Custom latitude to search from", type=openapi.TYPE_NUMBER),
            openapi.Parameter('longitude', openapi.IN_QUERY, description="Custom longitude to search from", type=openapi.TYPE_NUMBER),
            openapi.Parameter('distance', openapi.IN_QUERY, description="Radius distance in kilometers (defaults to user's distance_radius setting, or 25 if not set)", type=openapi.TYPE_NUMBER),
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