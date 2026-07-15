from rest_framework import permissions

class HasActiveSubscription(permissions.BasePermission):
    """
    Permission check to verify if the user has an active, non-expired subscription.
    This check applies to all operations (GET, POST, PUT, DELETE, etc.).
    """
    message = "An active subscription is required to access the Business listings API."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Check and update the user's subscription status dynamically
        return request.user.check_subscription()


class HasActiveSubscriptionForWrite(permissions.BasePermission):
    """
    Permission check to verify if the user has an active, non-expired subscription.
    Safe read-only operations (GET, HEAD, OPTIONS) are allowed for any authenticated user.
    Write operations (POST, PUT, PATCH, DELETE) require an active subscription.
    """
    message = "An active subscription is required to perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Allow read-only operations
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Check subscription for write operations
        return request.user.check_subscription()

