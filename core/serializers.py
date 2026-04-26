# core/serializers.py
import logging
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.settings import api_settings
from .models import Post, Page, Comment, Boost, Friendship

logger = logging.getLogger(__name__)
User = get_user_model()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Sérialiseur personnalisé pour l'authentification JWT par email.
    Accepte 'username' (qui contient l'email) et 'password'.
    """
    username_field = 'username'  # Le champ reçu du frontend
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre les champs obligatoires
        self.fields['username'].required = True
        self.fields['password'].required = True
        
    def validate(self, attrs):
        logger.info("\n=== Début validation MyTokenObtainPairSerializer ===")
        
        # Récupérer les données du frontend
        username_or_email = attrs.get('username', '').strip().lower()
        password = attrs.get('password', '')
        
        logger.info(f"Email reçu: {username_or_email}")
        logger.info(f"Password reçu: {'*' * len(password)}")
        
        if not username_or_email or not password:
            logger.error("Username/email ou password manquant")
            raise serializers.ValidationError(
                'Les champs email et mot de passe sont requis.',
                code='authorization'
            )
        
        # Authentifier avec notre backend personnalisé
        # On passe 'username' car c'est ce que le backend attend
        user = authenticate(
            request=self.context.get('request'),
            username=username_or_email,  # Notre EmailBackend utilisera ceci comme email
            password=password
        )
        
        if user is None:
            logger.error(f"Échec d'authentification pour: {username_or_email}")
            
            # Vérifier si l'utilisateur existe
            try:
                User.objects.get(email=username_or_email)
                logger.warning("L'utilisateur existe mais le mot de passe est incorrect")
                raise serializers.ValidationError(
                    'Mot de passe incorrect.',
                    code='authorization'
                )
            except User.DoesNotExist:
                logger.warning("Aucun utilisateur trouvé avec cet email")
                raise serializers.ValidationError(
                    'Aucun compte trouvé avec cet email.',
                    code='authorization'
                )
        
        if not user.is_active:
            logger.error(f"Compte désactivé pour: {username_or_email}")
            raise serializers.ValidationError(
                'Ce compte a été désactivé.',
                code='authorization'
            )
        
        logger.info(f"Authentification réussie pour l'utilisateur: {user.email}")
        
        # Générer les tokens
        refresh = self.get_token(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
        # Mettre à jour la dernière connexion
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)
        
        # Ajouter les informations de l'utilisateur
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        logger.info("Tokens générés avec succès")
        logger.info("=== Fin validation ===\n")
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """Sérialiseur pour afficher les informations utilisateur"""
    profile_picture_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cover_photo_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'profile_picture_url','cover_photo_url', 'city', 'gender', 'birth_date', 'interests', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un nouvel utilisateur"""
    password = serializers.CharField(write_only=True, min_length=8)
    re_password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 're_password', 'first_name', 'last_name']
        
    def validate_email(self, value):
        """Valider que l'email est unique"""
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un compte avec cet email existe déjà.")
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        re_password = attrs.get('re_password')
        if password != re_password:
            raise serializers.ValidationError({'re_password': "Les mots de passe ne correspondent pas."})
        return attrs
     
    def create(self, validated_data):
        """Créer un nouvel utilisateur avec mot de passe hashé"""
        validated_data['email'] = validated_data['email'].lower().strip()
        validated_data.pop('re_password', None)

        user = User.objects.create_user(**validated_data)
        return user


# Ajoutez vos autres sérialiseurs (Post, Page, Comment, etc.) ici
# core/serializers.py

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    is_liked = serializers.SerializerMethodField()
    relevance_score = serializers.FloatField(read_only=True, required=False)

    content = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    page = serializers.PrimaryKeyRelatedField(
        queryset=Page.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'page', 'content', 'media',
            'created_at', 'likes_count', 'comments_count',
            'is_liked', 'relevance_score'
        ]
        read_only_fields = ['author', 'created_at']

    def validate(self, attrs):
        content = (attrs.get('content') or '').strip()
        media = attrs.get('media') or []

        if not content and len(media) == 0:
            raise serializers.ValidationError({
                'content': "Ajoutez une description ou une photo/vidéo."
            })

        return attrs
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

class PageSerializer(serializers.ModelSerializer):
    subscribers_count = serializers.IntegerField(source='subscribers.count', read_only=True)
    profile_picture_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    cover_photo_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Page
        fields = [
            'id', 'owner', 'name', 'description', 
            'profile_picture_url', 'cover_photo_url', 
            'category', 'created_at', 'subscribers_count'
        ]
        read_only_fields = ['owner', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'content', 'parent_comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

class BoostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Boost
        fields = '__all__'
        read_only_fields = ['user', 'ranking_weight', 'status']
    
    def validate(self, data):
        audience_gender = data.get('audience_gender')
        if audience_gender is not None:
            audience_gender = str(audience_gender).upper()
            allowed_genders = {'ALL', 'MALE', 'FEMALE'}
            if audience_gender not in allowed_genders:
                raise serializers.ValidationError({
                    'audience_gender': "audience_gender doit être dans ['ALL', 'MALE', 'FEMALE']"
                })
            data['audience_gender'] = audience_gender

        audience_age_min = data.get('audience_age_min')
        audience_age_max = data.get('audience_age_max')
        if audience_age_min is not None and audience_age_min < 0:
            raise serializers.ValidationError({'audience_age_min': 'audience_age_min doit être >= 0'})
        if audience_age_max is not None and audience_age_max < 0:
            raise serializers.ValidationError({'audience_age_max': 'audience_age_max doit être >= 0'})
        if audience_age_min is not None and audience_age_max is not None and audience_age_min > audience_age_max:
            raise serializers.ValidationError('audience_age_min doit être <= audience_age_max')

        audience_interests = data.get('audience_interests', None)
        if audience_interests is not None:
            if not isinstance(audience_interests, list):
                raise serializers.ValidationError({'audience_interests': 'audience_interests doit être une liste de strings'})
            cleaned_interests = []
            for item in audience_interests:
                if not isinstance(item, str):
                    raise serializers.ValidationError({'audience_interests': 'audience_interests doit être une liste de strings'})
                cleaned = item.strip()
                if cleaned:
                    cleaned_interests.append(cleaned)
            data['audience_interests'] = cleaned_interests

        # Validation : si on booste un Post, il doit exister.
        # Option A: on autorise aussi les posts du profil (page=null).
        if data['target_type'] == 'POST':
            try:
                Post.objects.get(id=data['target_id'])
            except Post.DoesNotExist:
                raise serializers.ValidationError("Le Post ciblé n'existe pas.")
        return data


class FriendshipSerializer(serializers.ModelSerializer):
    requester = UserSerializer(read_only=True)
    addressee = UserSerializer(read_only=True)
    addressee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='addressee',
        write_only=True
    )

    class Meta:
        model = Friendship
        fields = ['id', 'requester', 'addressee', 'addressee_id', 'status', 'created_at']
        read_only_fields = ['requester', 'created_at']