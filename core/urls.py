from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'feed', FeedViewSet, basename='feed')
router.register(r'posts', PostViewSet)
router.register(r'pages', PageViewSet)
router.register(r'boosts', BoostViewSet, basename='boost')
router.register(r'friendships', FriendshipViewSet, basename='friendship')
router.register(r'comments', CommentViewSet)
router.register(r'upload', MediaUploadView, basename='upload')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', GlobalSearchView.as_view(), name='global-search'),
]

