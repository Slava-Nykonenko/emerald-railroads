from rest_framework.permissions import BasePermission, SAFE_METHODS


class AllowAnyListOnlyUserReadOnlyAdminAll(BasePermission):
    def has_permission(self, request, view):
        return bool(
            view.action == "list"
            or request.user and (
                request.user.is_authenticated
                and request.method in SAFE_METHODS
            )
            or request.user.is_staff
        )
