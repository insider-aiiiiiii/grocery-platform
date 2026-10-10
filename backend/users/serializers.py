from rest_framework import serializers

SUPER_ADMIN_RECOVERY_CHANNELS = (("EMAIL", "Email"), ("MOBILE", "Mobile"))


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
