from django.core.exceptions import PermissionDenied


class AdminAccessMiddleware:
    """Staff is the organizer role; only superusers may enter Django admin."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if (match and match.app_name == 'admin'
                and request.user.is_authenticated
                and not request.user.is_superuser):
            raise PermissionDenied('Only administrators can access this area.')
