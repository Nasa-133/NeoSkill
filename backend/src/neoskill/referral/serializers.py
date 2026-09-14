from rest_framework import serializers


class ReferralCodeSerializer(serializers.Serializer[dict[str, str]]):
    code = serializers.RegexField(r"(?i)^[23456789A-HJ-NP-Z]{12}$", max_length=12)

    def validate_code(self, value: str) -> str:
        return value.strip().upper()


class ReferralDiscountSerializer(serializers.Serializer[dict[str, int]]):
    discount_percent = serializers.IntegerField(min_value=0, max_value=100)
