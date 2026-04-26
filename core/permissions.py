from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée : lecture pour tous, écriture pour le propriétaire.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Pour Post, Page, Boost, etc.
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'author'):
            return obj.author == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False