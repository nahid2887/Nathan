from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    RegisterSerializer,
    RegisterSuccessResponseSerializer,
    RegisterErrorResponseSerializer,
    LoginSerializer,
    LoginSuccessResponseSerializer,
    LoginErrorResponseSerializer,
)
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class RegisterView(APIView):

    @extend_schema(
        summary="Register User",
        description="Create a new account and return JWT access and refresh tokens.",
        request=RegisterSerializer,
        responses={
            201: RegisterSuccessResponseSerializer,
            400: RegisterErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                "Registration Request",
                value={
                    "full_name": "Nahid Hasan",
                    "email": "nahid@gmail.com",
                    "password": "12345678",
                    "confirm_password": "12345678"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Successful Response",
                value={
                    "success": True,
                    "message": "User registered successfully.",
                    "access": "eyJhbGciOiJIUzI1NiIs...",
                    "refresh": "eyJhbGciOiJIUzI1NiIs...",
                    "user": {
                        "id": 1,
                        "full_name": "Nahid Hasan",
                        "email": "nahid@gmail.com"
                    }
                },
                response_only=True,
                status_codes=["201"]
            )
        ]
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

    @extend_schema(
        summary="Login User",
        description="Login with email and password and receive JWT tokens.",
        request=LoginSerializer,
        responses={
            200: LoginSuccessResponseSerializer,
            400: LoginErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                "Login Request",
                value={
                    "email": "nahid@gmail.com",
                    "password": "12345678"
                },
                request_only=True,
            ),
        ],
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

    @extend_schema(
        summary="Change Password",
        description="Change password for authenticated user.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "old_password": {
                        "type": "string",
                        "example": "12345678"
                    },
                    "new_password": {
                        "type": "string",
                        "example": "new_password_123"
                    },
                    "confirm_new_password": {
                        "type": "string",
                        "example": "new_password_123"
                    }
                },
                "required": [
                    "old_password",
                    "new_password",
                    "confirm_new_password"
                ]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "errors": {"type": "object"}
                }
            }
        },
        examples=[
            OpenApiExample(
                "Change Password Example",
                value={
                    "old_password": "12345678",
                    "new_password": "new_password_123",
                    "confirm_new_password": "new_password_123"
                },
                request_only=True,
            )
        ]
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