from django.contrib import admin
from .models import DealPlan, Deal, DealPhoto

class DealPhotoInline(admin.TabularInline):
    model = DealPhoto
    extra = 1

@admin.register(DealPlan)
class DealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle', 'discount_offer', 'active_deals_limit', 'created_at')
    list_filter = ('billing_cycle', 'is_most_popular')
    search_fields = ('name',)

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('title', 'business_name', 'category', 'deal_type', 'is_active', 'start_date', 'end_date', 'creator')
    list_filter = ('category', 'deal_type', 'is_active', 'business_type')
    search_fields = ('title', 'business_name', 'creator__email')
    inlines = [DealPhotoInline]
