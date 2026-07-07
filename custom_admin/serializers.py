from rest_framework import serializers
from .models import SubscriptionPlan

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'price', 'billing_cycle', 
            'discount_offer', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_discount_offer(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Discount offer percentage must be between 0 and 100.")
        return value
