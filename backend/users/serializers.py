from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SuperAdminLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


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
