from rest_framework import serializers


class CustomerCancellationSerializer(serializers.Serializer):
    confirmed = serializers.BooleanField(required=True)

    def to_internal_value(self, data):
        if not hasattr(data, "keys"):
            raise serializers.ValidationError("A JSON object is required.")
        unknown = set(data.keys()) - {"confirmed"}
        if unknown:
            raise serializers.ValidationError({key: "Unknown or unsupported field." for key in unknown})
        return super().to_internal_value(data)

    def validate_confirmed(self, value):
        if value is not True:
            raise serializers.ValidationError("Explicit confirmation is required.")
        return value
