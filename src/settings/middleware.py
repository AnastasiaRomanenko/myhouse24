from django.contrib.auth.views import redirect_to_login

from src.users.enums import Status


class SettingsAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/settings/"):
            user = request.user
            if not (
                user.is_authenticated
                and user.is_staff
                and user.is_active
                and user.status == Status.ACTIVE
            ):
                return redirect_to_login(request.get_full_path())
        return self.get_response(request)
