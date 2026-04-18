from django.contrib import admin
from .models import Resource, Booking, UserProfile, ActionLog


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'resource_type',
        'department',
        'location',
        'capacity',
        'is_active',
        'created_at',
    )
    list_filter = ('resource_type', 'department', 'is_active')
    search_fields = ('name', 'location')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('resource', 'user', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'resource')
    search_fields = ('resource__name', 'user__username')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action_type', 'object_type', 'object_repr')
    list_filter = ('action_type', 'object_type')
    search_fields = ('user__username', 'object_repr', 'description')