from django.contrib import admin
from .models import Event, Category, Registration, EventFeedback


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'date', 'venue', 'capacity', 'status', 'featured']
    list_filter = ['status', 'category', 'featured', 'is_free']
    search_fields = ['title', 'venue', 'description']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'date'
    list_editable = ['status', 'featured']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'status', 'ticket_number', 'registration_date']
    list_filter = ['status']
    search_fields = ['user__username', 'event__title', 'ticket_number']
    readonly_fields = ['ticket_number', 'registration_date']


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['user__username', 'event__title']
