import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

# --- Enum Choices ---
class TargetType(models.TextChoices):
    PAGE = 'PAGE', 'Page'
    POST = 'POST', 'Post'

class BoostStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    COMPLETED = 'COMPLETED', 'Completed'

class FriendStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    DECLINED = 'DECLINED', 'Declined'
    BLOCKED = 'BLOCKED', 'Blocked'

# --- Models ---

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username_validator = UnicodeUsernameValidator()

    # Redéfini pour enlever l'unicité (obligatoire mais pas unique)
    username = models.CharField(
        'username',
        max_length=150,
        unique=False,
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        validators=[username_validator],
        error_messages={},
    )
    email = models.EmailField(unique=True, blank=False, null=False)
    profile_picture_url = models.URLField(blank=True, null=True)
    cover_photo_url = models.URLField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    interests = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    # Pour éviter les conflits avec le système auth par défaut de Django
    groups = models.ManyToManyField('auth.Group', related_name='custom_user_set', blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='custom_user_set', blank=True)

    def __str__(self):
        return self.email
    class Meta:
        verbose_name = "Utilisateur"
        ordering = ['-created_at']

class Page(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pages')
    name = models.CharField(max_length=255)
    description = models.TextField()
    profile_picture_url = models.URLField(blank=True, null=True)
    cover_photo_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    subscribers = models.ManyToManyField(User, through='PageSubscription', related_name='subscribed_pages')

    def __str__(self):
        return self.name

class PageSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'page')

class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    content = models.TextField()
    # On stocke les médias en JSON: [{"type": "IMAGE", "url": "..."}]
    media = models.JSONField(default=list, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Validation métier : Un boost ne peut cibler un post que si page_id n'est pas null 
        # (Cette validation est souvent faite au niveau du serializer ou du modèle Boost, 
        # ici on garde le Post simple).
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']), # Pour accélérer le Feed
        ]

    @property
    def total_likes(self):
        return self.likes.count()

    @property
    def total_comments(self):
        return self.comments.count()    

class Boost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Cible polymorphique simplifiée
    target_id = models.UUIDField()
    target_type = models.CharField(max_length=10, choices=TargetType.choices)
    
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=BoostStatus.choices, default=BoostStatus.ACTIVE)
    ranking_weight = models.IntegerField(default=0)
    audience_location = models.CharField(max_length=100, blank=True, null=True)
    audience_age_min = models.IntegerField(blank=True, null=True)
    audience_age_max = models.IntegerField(blank=True, null=True)
    audience_gender = models.CharField(max_length=10, blank=True, null=True)
    audience_interests = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        self.calculate_weight()
        super().save(*args, **kwargs)

    def calculate_weight(self):
        # Logique métier interne
        weight = 0
        if self.target_type == TargetType.POST:
            weight = 100
        elif self.target_type == TargetType.PAGE:
            weight = 50
        
        # Bonus selon le budget (exemple: +1 point par 10$)
        weight += int(self.budget / 10)
        self.ranking_weight = weight

class Friendship(models.Model):
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    addressee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=20, choices=FriendStatus.choices, default=FriendStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('requester', 'addressee')

# Interactions
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('user', 'post')

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    parent_comment = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Share(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')