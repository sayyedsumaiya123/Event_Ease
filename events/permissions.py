"""Role and ownership checks shared by event management views."""
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser


class OrganizerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_active and (user.is_staff or user.is_superuser)


def managed_events(user, queryset):
    if user.is_superuser:
        return queryset
    return queryset.filter(Q(organizer=user) | Q(coordinators=user)).distinct()


class ManagedEventMixin:
    """Scope object lookup for both GET and POST, including attendance views."""
    def get_queryset(self):
        return managed_events(self.request.user, super().get_queryset())


class EventFormUserMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
