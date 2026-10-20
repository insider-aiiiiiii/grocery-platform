from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Merchant, User

SUPER_ADMIN_RECOVERY_CHANNELS = (("EMAIL", "Email"), ("MOBILE", "Mobile"))


class LoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SuperAdminLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SuperAdminCreateMerchantSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    mobile_number = serializers.CharField(
        max_length=32,
        trim_whitespace=False,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    initial_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_initial_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        password = validated_data.pop("initial_password")
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data.get("email", ""),
                mobile_number=validated_data["mobile_number"],
                password=password,
                role=User.Role.MERCHANT,
            )
            return Merchant.objects.create(user=user, must_change_password=True)


class SuperAdminCreatedMerchantSerializer(serializers.Serializer):
    merchant_id = serializers.IntegerField(source="id")
    user_id = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    mobile_number = serializers.CharField(source="user.mobile_number")
    email = serializers.EmailField(source="user.email")
    role = serializers.CharField(source="user.role")
    status = serializers.CharField()
    must_change_password = serializers.BooleanField()


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class LogoutSerializer(RefreshSerializer):
    pass


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class MerchantPasswordRecoveryRequestSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=32, trim_whitespace=False)


class MerchantPasswordRecoveryConfirmSerializer(MerchantPasswordRecoveryRequestSerializer):
    otp = serializers.RegexField(regex=r"^[0-9]{7}$", write_only=True)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class SuperAdminRecoveryContactSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=SUPER_ADMIN_RECOVERY_CHANNELS)
    contact = serializers.CharField(max_length=254, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["channel"] == "EMAIL":
            attrs["contact"] = serializers.EmailField().run_validation(attrs["contact"])
        elif len(attrs["contact"]) > 32:
            raise serializers.ValidationError({"contact": "Ensure this field has no more than 32 characters."})
        return attrs


class SuperAdminRecoveryConfirmSerializer(SuperAdminRecoveryContactSerializer):
    code = serializers.RegexField(regex=r"^[0-9]{7}$", write_only=True)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class SuperAdminAdministrativeResetRequestSerializer(serializers.Serializer):
    target_user_id = serializers.IntegerField(min_value=1)
    channel = serializers.ChoiceField(choices=SUPER_ADMIN_RECOVERY_CHANNELS)
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)


class SuperAdminAdministrativeResetConfirmSerializer(SuperAdminRecoveryConfirmSerializer):
    pass
