from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")

        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["full_name"]
        )

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})
        if attrs['new_password'] == attrs['old_password']:
            raise serializers.ValidationError({"new_password": "New password cannot be the same as the old password."})
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    is_subscribed = serializers.BooleanField(required=False)
    subscription_expiry = serializers.DateTimeField(required=False)


class RegisterSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserResponseSerializer()


class RegisterErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    errors = serializers.DictField()



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user_obj = User.objects.filter(email=email).first()
        username = user_obj.username if user_obj else email

        user = authenticate(
            username=username,
            password=password
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        attrs["user"] = user
        return attrs



class LoginUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    is_subscribed = serializers.BooleanField(required=False)
    subscription_expiry = serializers.DateTimeField(required=False)


class LoginSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = LoginUserSerializer()


class LoginErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    errors = serializers.DictField()


class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', required=False, allow_blank=True)
    email = serializers.EmailField(read_only=True)
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'profile_photo', 'latitude', 'longitude', 
            'distance_radius', 'about_me', 'location_name', 'notify_events', 
            'notify_recommendations', 'notify_looking_for',
            'is_subscribed', 'subscription_expiry'
        ]
        read_only_fields = ['id', 'email', 'is_subscribed', 'subscription_expiry']


class ProfileResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    profile = ProfileSerializer()


class ProfileUpdateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    profile = ProfileSerializer()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')

        from .models import OTP
        otp_record = OTP.objects.filter(email=email, code=otp).last()

        if not otp_record:
            raise serializers.ValidationError({"otp": "Invalid OTP code."})

        if otp_record.is_expired():
            raise serializers.ValidationError({"otp": "OTP code has expired."})

        if otp_record.is_verified:
            raise serializers.ValidationError({"otp": "OTP has already been verified."})

        attrs['otp_record'] = otp_record
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')

        if password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        from .models import OTP
        otp_record = OTP.objects.filter(email=email, is_verified=True).last()
        if not otp_record or otp_record.is_expired():
            raise serializers.ValidationError({"email": "OTP has not been verified for this email, or has expired."})

        attrs['otp_record'] = otp_record
        return attrs


class NearbyUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo', 'latitude', 'longitude', 'distance_km']
        read_only_fields = fields

    def get_distance_km(self, obj):
        return getattr(obj, 'distance_km', None)


class FriendUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'profile_photo', 'latitude', 'longitude']
        read_only_fields = fields


class FriendRequestSerializer(serializers.ModelSerializer):
    sender = FriendUserSerializer(read_only=True)

    class Meta:
        from .models import Friendship
        model = Friendship
        fields = ['id', 'sender', 'created_at']
        read_only_fields = fields


class MyItemsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    items = serializers.ListField(child=serializers.DictField())