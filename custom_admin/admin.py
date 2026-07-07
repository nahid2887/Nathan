from django.contrib import admin
from .models import SubscriptionPlan

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'name', 
        'price', 
        'billing_cycle', 
        'discount_offer', 
        'created_at', 
        'updated_at'
    )
    list_filter = ('billing_cycle', 'created_at')
    search_fields = ('name',)
    ordering = ('-created_at',)
