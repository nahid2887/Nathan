from rest_framework import permissions

class HasActiveSubscription(permissions.BasePermission):
    """
    Permission check to verify if the user has an active, non-expired subscription.
    This check applies to all operations (GET, POST, PUT, DELETE, etc.).
    """
    message = "An active subscription is required to access the Product Ads API."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Check and update the user's subscription status dynamically
        return request.user.check_subscription()


class IsCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a product ad to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator
        return obj.creator == request.user
