from django.contrib import admin
from .models import User, Page, Post, Boost, PageSubscription, Like, Comment, Share

# Enregistrement des modèles
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'page', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content',)

@admin.register(Boost)
class BoostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'target_type', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'target_type', 'start_date', 'end_date')

@admin.register(PageSubscription)
class PageSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'page', 'subscribed_at')
    list_filter = ('subscribed_at',)

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('content',)

@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'id')