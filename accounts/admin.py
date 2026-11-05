from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_organizer', 'phone', 'organization', 'location', 'created_at']
    search_fields = ['user__username', 'user__email', 'organization']
    readonly_fields = ['created_at', 'updated_at']
