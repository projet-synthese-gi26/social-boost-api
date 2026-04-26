import logging
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, F, Case, When, Value, IntegerField, FloatField, ExpressionWrapper, Count
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .serializers import MyTokenObtainPairSerializer
from .models import *
from .serializers import *
from .permissions import IsOwnerOrReadOnly

logger = logging.getLogger(__name__)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info("\n=== Requête de connexion reçue ===")
        logger.info(f"Données reçues: {request.data}")

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            logger.info("Validation réussie, retour des tokens")
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {str(e)}")

            error_message = 'Email ou mot de passe incorrect.'
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
                    for key, value in e.detail.items():
                        if isinstance(value, list):
                            error_message = value[0] if value else error_message
                        else:
                            error_message = value
                        break
                elif isinstance(e.detail, list):
                    error_message = e.detail[0] if e.detail else error_message
                else:
                    error_message = str(e.detail)

            return Response({'detail': error_message}, status=status.HTTP_401_UNAUTHORIZED)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    @action(detail=True, methods=['get'])
    def friends(self, request, id=None):
        user = self.get_object()
        fships = Friendship.objects.filter(
            (Q(requester=user) | Q(addressee=user)),
            status=FriendStatus.ACCEPTED
        )
        friend_ids = [f.addressee_id if f.requester_id == user.id else f.requester_id for f in fships]
        friends = User.objects.filter(id__in=friend_ids)
        return Response(UserSerializer(friends, many=True).data)

    @action(detail=True, methods=['get'])
    def mutual_friends(self, request, id=None):
        target_user = self.get_object()
        me = request.user

        if target_user == me:
            return Response([])

        my_fships = Friendship.objects.filter(
            (Q(requester=me) | Q(addressee=me)),
            status=FriendStatus.ACCEPTED
        )
        their_fships = Friendship.objects.filter(
            (Q(requester=target_user) | Q(addressee=target_user)),
            status=FriendStatus.ACCEPTED
        )

        my_friend_ids = {f.addressee_id if f.requester_id == me.id else f.requester_id for f in my_fships}
        their_friend_ids = {f.addressee_id if f.requester_id == target_user.id else f.requester_id for f in their_fships}

        mutual_ids = my_friend_ids.intersection(their_friend_ids)
        mutual_users = User.objects.filter(id__in=mutual_ids)
        return Response(UserSerializer(mutual_users, many=True).data)

    @action(detail=True, methods=['get'])
    def posts(self, request, id=None):
        user = self.get_object()
        qs = (
            Post.objects.filter(Q(author=user) | Q(page__owner=user))
            .select_related('author', 'page')
            .order_by('-created_at')
        )
        serializer = PostSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()

        viewer_city = (getattr(user, 'city', None) or '').strip().lower()
        viewer_gender = (getattr(user, 'gender', None) or '').strip().upper()

        viewer_interests_raw = getattr(user, 'interests', None) or []
        viewer_interests = {
            i.strip() for i in viewer_interests_raw
            if isinstance(i, str) and i.strip()
        }

        viewer_age = None
        viewer_birth_date = getattr(user, 'birth_date', None)
        if viewer_birth_date:
            today = now.date()
            viewer_age = today.year - viewer_birth_date.year
            if (today.month, today.day) < (viewer_birth_date.month, viewer_birth_date.day):
                viewer_age -= 1

        def compute_audience_match_bonus(boost_obj):
            bonus = 0

            boost_location = (getattr(boost_obj, 'audience_location', None) or '').strip().lower()
            if boost_location and viewer_city and viewer_city in boost_location:
                bonus += 20

            boost_gender = (getattr(boost_obj, 'audience_gender', None) or '').strip().upper()
            if boost_gender and boost_gender != 'ALL' and viewer_gender and viewer_gender == boost_gender:
                bonus += 10

            age_min = getattr(boost_obj, 'audience_age_min', None)
            age_max = getattr(boost_obj, 'audience_age_max', None)
            if viewer_age is not None and (age_min is not None or age_max is not None):
                ok_min = age_min is None or viewer_age >= age_min
                ok_max = age_max is None or viewer_age <= age_max
                if ok_min and ok_max:
                    bonus += 10

            boost_interests_raw = getattr(boost_obj, 'audience_interests', None) or []
            boost_interests = {
                i.strip() for i in boost_interests_raw
                if isinstance(i, str) and i.strip()
            }
            if boost_interests and viewer_interests:
                common = boost_interests.intersection(viewer_interests)
                bonus += min(20, 5 * len(common))

            return bonus

        friend_pairs = Friendship.objects.filter(
            Q(requester=user) | Q(addressee=user),
            status=FriendStatus.ACCEPTED
        ).values_list('requester_id', 'addressee_id')
        friend_ids_flat = {uid for sublist in friend_pairs for uid in sublist if uid != user.id}
        subscribed_page_ids = PageSubscription.objects.filter(user=user).values_list('page_id', flat=True)

        active_boosts = Boost.objects.filter(
            status=BoostStatus.ACTIVE,
            start_date__lte=now,
            end_date__gte=now,
        )

        post_boost_bonus_map = {}
        page_boost_bonus_map = {}

        for boost in active_boosts:
            audience_bonus = compute_audience_match_bonus(boost)
            if boost.target_type == TargetType.POST:
                post_boost_bonus_map[boost.target_id] = 100 + audience_bonus
            elif boost.target_type == TargetType.PAGE:
                page_boost_bonus_map[boost.target_id] = 60 + audience_bonus

        queryset = Post.objects.all().annotate(
            num_likes=Count('likes', distinct=True),
            num_comments=Count('comments', distinct=True),
        )

        w_affinity = Case(
            When(author__in=friend_ids_flat, then=Value(40)),
            When(page__in=subscribed_page_ids, then=Value(35)),
            default=Value(0),
            output_field=IntegerField(),
        )

        boost_whens = []
        for post_id, bonus in post_boost_bonus_map.items():
            boost_whens.append(When(id=post_id, then=Value(bonus)))
        for page_id, bonus in page_boost_bonus_map.items():
            boost_whens.append(When(page_id=page_id, then=Value(bonus)))

        if boost_whens:
                w_boost = Case(*boost_whens, default=Value(0), output_field=IntegerField())
        else:
            w_boost = Value(0)

        w_boost = Case(
            *boost_whens,
            default=Value(0),
            output_field=IntegerField(),
        )

        w_engagement = ExpressionWrapper(
            (F('num_likes') * 2) + (F('num_comments') * 5),
            output_field=IntegerField(),
        )

        w_content = Case(
            When(~Q(media=[]), then=Value(15)),
            default=Value(0),
            output_field=IntegerField(),
        )

        w_freshness = Case(
            When(created_at__gte=now - timedelta(days=1), then=Value(50)),
            When(created_at__gte=now - timedelta(days=3), then=Value(20)),
            default=Value(0),
            output_field=IntegerField(),
        )

        queryset = queryset.annotate(
            relevance_score=ExpressionWrapper(
                w_affinity + w_boost + w_engagement + w_content + w_freshness + Value(1),
                output_field=FloatField(),
            )
        )

        return queryset.select_related('author', 'page').order_by('-relevance_score', '-created_at')


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsOwnerOrReadOnly, IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mine(self, request):
        qs = Post.objects.filter(
            Q(author=request.user) | Q(page__owner=request.user)
        ).select_related('author', 'page').order_by('-created_at')

        serializer = self.get_serializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        Like.objects.get_or_create(user=request.user, post=post)
        return Response({'status': 'liked'})

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        post = self.get_object()
        Like.objects.filter(user=request.user, post=post).delete()
        return Response({'status': 'unliked'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def share(self, request, pk=None):
        post = self.get_object()
        Share.objects.create(user=request.user, post=post)
        return Response({'status': 'shared'})


class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'id'

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, 'action', None) == 'list':
            return queryset.filter(owner=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        page = self.get_object()
        PageSubscription.objects.get_or_create(user=request.user, page=page)
        return Response({'status': 'subscribed'})

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unsubscribe(self, request, id=None):
        page = self.get_object()
        PageSubscription.objects.filter(user=request.user, page=page).delete()
        return Response({'status': 'unsubscribed'})

    @action(detail=True, methods=['get'])
    def posts(self, request, id=None):
        page = self.get_object()
        posts = Post.objects.filter(page=page)
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)


class BoostViewSet(viewsets.ModelViewSet):
    serializer_class = BoostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Boost.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=BoostStatus.PAUSED)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        boost = self.get_object()

        payment_token = request.data.get('payment_token')
        amount = request.data.get('amount')

        if not payment_token:
            return Response({'error': 'Token de paiement manquant'}, status=400)

        if float(amount) < float(boost.budget):
            return Response({'error': 'Montant insuffisant pour le budget défini'}, status=400)

        boost.status = BoostStatus.ACTIVE
        boost.save()

        return Response({
            'status': 'success',
            'message': 'Paiement accepté, Boost activé.',
            'boost_status': boost.status,
        })

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        boost = self.get_object()
        if boost.status != BoostStatus.ACTIVE:
            return Response(
                {'error': 'Seuls les boosts actifs peuvent être mis en pause.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        boost.status = BoostStatus.PAUSED
        boost.save()
        return Response({'status': 'success', 'boost_status': boost.status})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        boost = self.get_object()
        if boost.status != BoostStatus.PAUSED:
            return Response(
                {'error': 'Seuls les boosts en pause peuvent être repris.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        boost.status = BoostStatus.ACTIVE
        boost.save()
        return Response({'status': 'success', 'boost_status': boost.status})

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        boost = self.get_object()
        if boost.status == BoostStatus.COMPLETED:
            return Response(
                {'error': 'Ce boost est déjà terminé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        boost.status = BoostStatus.COMPLETED
        boost.end_date = timezone.now()
        boost.save()
        return Response({'status': 'success', 'boost_status': boost.status})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Comment.objects.all()
        post_id = self.request.query_params.get('post')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FriendshipViewSet(viewsets.ModelViewSet):
    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Friendship.objects.filter(
            Q(requester=self.request.user) | Q(addressee=self.request.user)
        )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        addressee = serializer.validated_data['addressee']
        requester = request.user

        if addressee == requester:
            return Response({'detail': "Vous ne pouvez pas vous ajouter en ami."}, status=status.HTTP_400_BAD_REQUEST)

        existing = Friendship.objects.filter(
            Q(requester=requester, addressee=addressee) |
            Q(requester=addressee, addressee=requester)
        ).first()

        if existing:
            existing_data = self.get_serializer(existing).data
            return Response(existing_data, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        addressee = serializer.validated_data['addressee']
        requester = self.request.user

        if addressee == requester:
            raise serializers.ValidationError("Vous ne pouvez pas vous ajouter en ami.")
        serializer.save(requester=requester, status=FriendStatus.PENDING)
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        friendship = self.get_object()
        if friendship.addressee != request.user:

            return Response({'error': 'Ce n\'est pas votre demande.'}, status=403)
        
        friendship.status = FriendStatus.ACCEPTED
        friendship.save()
        return Response({'status': 'friendship accepted'})
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        friendship = self.get_object()
        if friendship.addressee != request.user:
            return Response({'error': 'Action non autorisée.'}, status=403)
        
        friendship.status = FriendStatus.DECLINED
        friendship.save()
        return Response({'status': 'friendship declined'})
    # --- NOUVELLE ACTION AJOUTÉE ---
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        user = request.user
        # 1. Récupérer les IDs des utilisateurs déjà liés
        connected_user_ids = Friendship.objects.filter(
            Q(requester=user) | Q(addressee=user)
        ).values_list('requester_id', 'addressee_id')
        # Aplatir la liste et exclure l'utilisateur actuel
        excluded_ids = {uid for pair in connected_user_ids for uid in pair}
        excluded_ids.add(user.id)
        # 2. Obtenir jusqu'à 10 utilisateurs qui ne sont pas dans la liste d'exclusion
        suggested_users = User.objects.exclude(id__in=excluded_ids).order_by('?')[:10]
        # 3. Sérialiser et renvoyer les données
        serializer = UserSerializer(suggested_users, many=True)
        return Response(serializer.data)

class MediaUploadView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'Aucun fichier fourni'}, status=400)
        
        # 1. Extraire l'extension et préparer un nom unique
        ext = file_obj.name.split('.')[-1].lower()
        # On définit le nom du fichier (Cloudinary créera les dossiers automatiquement)
        filename = f"uploads/{request.user.id}/{uuid.uuid4()}.{ext}"
        
        # 2. Sauvegarder le fichier
        # Si DEFAULT_FILE_STORAGE est configuré sur Cloudinary, 
        # cette ligne envoie le fichier directement sur leurs serveurs.
        path = default_storage.save(filename, ContentFile(file_obj.read()))
        
        # 3. RÉCUPÉRATION DE L'URL (LA CORRECTION EST ICI)
        # default_storage.url(path) détecte automatiquement si l'image est sur Cloudinary 
        # et renvoie l'URL complète commençant par https://res.cloudinary.com/...
        url = default_storage.url(path)
        
        return Response({
            'url': url, 
            'type': 'IMAGE' if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else 'VIDEO'
        })
        
class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({'users': [], 'pages': []}, status=200)

        # 1. Recherche des utilisateurs (Prénom ou Nom)
        users = User.objects.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(email__icontains=query) # Optionnel: recherche par email aussi
        ).distinct()[:10] # On limite à 10 résultats pour la performance

        # 2. Recherche des pages (Nom)
        pages = Page.objects.filter(
            name__icontains=query
        ).distinct()[:10]

        # 3. Sérialisation
        user_serializer = UserSerializer(users, many=True)
        page_serializer = PageSerializer(pages, many=True)

        return Response({
            'users': user_serializer.data,
            'pages': page_serializer.data
        }, status=status.HTTP_200_OK)        