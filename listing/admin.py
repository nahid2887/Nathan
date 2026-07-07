from django.contrib import admin
from .models import Listing, ListingPhoto

class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 1

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'title', 
        'creator', 
        'category', 
        'status', 
        'price', 
        'condition', 
        'location_name', 
        'created_at'
    )
    list_filter = ('status', 'condition', 'category', 'created_at')
    search_fields = (
        'title', 
        'description', 
        'location_name', 
        'creator__email', 
        'creator__username'
    )
    ordering = ('-created_at',)
    inlines = [ListingPhotoInline]

@admin.register(ListingPhoto)
class ListingPhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'image', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('listing__title', 'listing__creator__email')
