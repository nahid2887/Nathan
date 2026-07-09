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
