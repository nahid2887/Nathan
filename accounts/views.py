from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

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