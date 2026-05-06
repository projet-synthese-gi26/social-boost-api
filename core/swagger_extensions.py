# core/swagger_extensions.py
"""
Extensions OpenAPI / drf-spectacular pour documenter tous les endpoints
du backend Boost Social Network.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

# ─────────────────────────────────────────────────────────────────────────────
# Schémas inline réutilisables
# ─────────────────────────────────────────────────────────────────────────────

TokenResponseSchema = inline_serializer(
    name="TokenResponse",
    fields={
        "access": serializers.CharField(help_text="JWT Access Token (valide 60 min)"),
        "refresh": serializers.CharField(help_text="JWT Refresh Token (valide 7 jours)"),
        "user": inline_serializer(
            name="TokenUserInfo",
            fields={
                "id": serializers.UUIDField(),
                "email": serializers.EmailField(),
                "first_name": serializers.CharField(),
                "last_name": serializers.CharField(),
            },
        ),
    },
)

TokenRefreshResponseSchema = inline_serializer(
    name="TokenRefreshResponse",
    fields={
        "access": serializers.CharField(help_text="Nouveau JWT Access Token"),
    },
)

StatusResponseSchema = inline_serializer(
    name="StatusResponse",
    fields={"status": serializers.CharField()},
)

PayBoostRequestSchema = inline_serializer(
    name="PayBoostRequest",
    fields={
        "payment_token": serializers.CharField(
            help_text="Token de paiement (ex: tok_visa depuis Stripe)"
        ),
        "amount": serializers.DecimalField(
            max_digits=10,
            decimal_places=2,
            help_text="Montant payé — doit être >= budget du boost",
        ),
    },
)

PayBoostResponseSchema = inline_serializer(
    name="PayBoostResponse",
    fields={
        "status": serializers.CharField(),
        "message": serializers.CharField(),
        "boost_status": serializers.CharField(),
    },
)

SearchResponseSchema = inline_serializer(
    name="SearchResponse",
    fields={
        "users": serializers.ListField(
            child=serializers.DictField(),
            help_text="Liste des utilisateurs correspondant à la recherche",
        ),
        "pages": serializers.ListField(
            child=serializers.DictField(),
            help_text="Liste des pages correspondant à la recherche",
        ),
    },
)

UploadResponseSchema = inline_serializer(
    name="UploadResponse",
    fields={
        "url": serializers.URLField(
            help_text="URL publique du fichier uploadé (Cloudinary)"
        ),
        "type": serializers.ChoiceField(
            choices=["IMAGE", "VIDEO"],
            help_text="Type de média détecté",
        ),
    },
)

# ─────────────────────────────────────────────────────────────────────────────
# Decorateurs pour les ViewSets — importez-les dans views.py
# ─────────────────────────────────────────────────────────────────────────────

# ── Auth ──────────────────────────────────────────────────────────────────────
token_obtain_schema = extend_schema(
    tags=["🔐 Authentification"],
    summary="Connexion — Obtenir les tokens JWT",
    description=(
        "Authentifie un utilisateur avec son **email** et son **mot de passe**. "
        "Retourne un access token (60 min) et un refresh token (7 jours), "
        "ainsi que les informations de base de l'utilisateur connecté.\n\n"
        "> ⚠️ Le champ s'appelle `username` mais il attend un **email**."
    ),
    request=inline_serializer(
        name="TokenObtainRequest",
        fields={
            "username": serializers.EmailField(
                help_text="L'adresse email de l'utilisateur"
            ),
            "password": serializers.CharField(
                help_text="Mot de passe (min. 8 caractères)"
            ),
        },
    ),
    responses={
        200: TokenResponseSchema,
        401: OpenApiResponse(description="Email ou mot de passe incorrect"),
    },
    examples=[
        OpenApiExample(
            "Exemple de connexion",
            value={"username": "alice@example.com", "password": "motdepasse123"},
            request_only=True,
        ),
        OpenApiExample(
            "Réponse succès",
            value={
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "04d87a6a-3766-46ec-8e32-c7cae65bb101",
                    "email": "alice@example.com",
                    "first_name": "Alice",
                    "last_name": "Dupont",
                },
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)

token_refresh_schema = extend_schema(
    tags=["🔐 Authentification"],
    summary="Rafraîchir l'access token",
    description=(
        "Génère un nouvel **access token** à partir d'un refresh token valide. "
        "À appeler lorsque l'access token a expiré (après 60 min)."
    ),
    request=inline_serializer(
        name="TokenRefreshRequest",
        fields={
            "refresh": serializers.CharField(
                help_text="Le refresh token obtenu lors de la connexion"
            )
        },
    ),
    responses={
        200: TokenRefreshResponseSchema,
        401: OpenApiResponse(description="Refresh token invalide ou expiré"),
    },
)

# ── Registration (Djoser) ─────────────────────────────────────────────────────
register_schema = extend_schema(
    tags=["🔐 Authentification"],
    summary="Inscription — Créer un compte",
    description=(
        "Crée un nouvel utilisateur. "
        "Les mots de passe doivent correspondre et faire au minimum 8 caractères. "
        "L'email doit être unique."
    ),
    request=inline_serializer(
        name="RegisterRequest",
        fields={
            "email": serializers.EmailField(help_text="Email unique, utilisé comme identifiant"),
            "username": serializers.CharField(help_text="Nom d'affichage (non unique)"),
            "first_name": serializers.CharField(help_text="Prénom"),
            "last_name": serializers.CharField(help_text="Nom de famille"),
            "password": serializers.CharField(help_text="Mot de passe (min. 8 caractères)"),
            "re_password": serializers.CharField(help_text="Confirmation du mot de passe"),
        },
    ),
    responses={
        201: OpenApiResponse(description="Compte créé avec succès"),
        400: OpenApiResponse(description="Données invalides ou email déjà utilisé"),
    },
    examples=[
        OpenApiExample(
            "Exemple d'inscription",
            value={
                "email": "bob@example.com",
                "username": "bobito",
                "first_name": "Bob",
                "last_name": "Martin",
                "password": "superSecret1!",
                "re_password": "superSecret1!",
            },
            request_only=True,
        )
    ],
)

# ── Users ─────────────────────────────────────────────────────────────────────
user_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["👤 Utilisateurs"],
        summary="Lister tous les utilisateurs",
        description="Retourne la liste paginée de tous les utilisateurs enregistrés.",
    ),
    retrieve=extend_schema(
        tags=["👤 Utilisateurs"],
        summary="Obtenir un utilisateur par ID",
        description="Retourne le profil complet d'un utilisateur à partir de son UUID.",
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="UUID de l'utilisateur",
            )
        ],
    ),
)

user_friends_schema = extend_schema(
    tags=["👤 Utilisateurs"],
    summary="Amis d'un utilisateur",
    description="Retourne la liste des amis acceptés d'un utilisateur donné.",
    responses={200: OpenApiResponse(description="Liste des amis")},
)

user_mutual_friends_schema = extend_schema(
    tags=["👤 Utilisateurs"],
    summary="Amis en commun",
    description=(
        "Retourne les amis **en commun** entre l'utilisateur connecté "
        "et l'utilisateur ciblé."
    ),
    responses={200: OpenApiResponse(description="Liste des amis en commun")},
)

user_posts_schema = extend_schema(
    tags=["👤 Utilisateurs"],
    summary="Publications d'un utilisateur",
    description=(
        "Retourne tous les posts publiés par un utilisateur, "
        "qu'ils soient sur son profil ou sur une page qu'il possède."
    ),
    responses={200: OpenApiResponse(description="Liste des posts")},
)

# ── Feed ──────────────────────────────────────────────────────────────────────
feed_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["📰 Feed"],
        summary="Fil d'actualité personnalisé",
        description=(
            "Retourne les publications triées par un **score de pertinence** calculé "
            "à partir de plusieurs facteurs :\n\n"
            "| Facteur | Points |\n"
            "|---|---|\n"
            "| Post d'un ami | +40 |\n"
            "| Post d'une page abonnée | +35 |\n"
            "| Boost actif (post ciblé) | +100 + bonus audience |\n"
            "| Boost actif (page ciblée) | +60 + bonus audience |\n"
            "| Engagement (likes × 2 + comments × 5) | variable |\n"
            "| Contient des médias | +15 |\n"
            "| Fraîcheur < 24h | +50 |\n"
            "| Fraîcheur < 3 jours | +20 |\n\n"
            "Le **bonus audience** d'un boost est calculé selon la correspondance "
            "avec le profil du viewer (ville, genre, âge, centres d'intérêt)."
        ),
        responses={200: OpenApiResponse(description="Liste paginée de posts avec relevance_score")},
    ),
    retrieve=extend_schema(
        tags=["📰 Feed"],
        summary="Détail d'un post (depuis le feed)",
        description="Retourne un post unique avec son score de pertinence.",
    ),
)

# ── Posts ─────────────────────────────────────────────────────────────────────
post_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["📝 Posts"],
        summary="Lister tous les posts",
        description="Retourne la liste paginée de tous les posts, du plus récent au plus ancien.",
    ),
    create=extend_schema(
        tags=["📝 Posts"],
        summary="Créer un post",
        description=(
            "Crée un nouveau post. Au moins un **contenu texte** ou un **média** "
            "est obligatoire. Le champ `media` est une liste JSON d'objets "
            "`{type, url}` obtenus via l'endpoint `/api/upload/`.\n\n"
            "Pour publier sur une page, renseignez `page` avec l'UUID de la page "
            "(vous devez en être le propriétaire)."
        ),
        examples=[
            OpenApiExample(
                "Post texte simple",
                value={"content": "Bonjour le monde 🌍", "media": []},
                request_only=True,
            ),
            OpenApiExample(
                "Post avec image",
                value={
                    "content": "Regardez cette belle photo !",
                    "media": [
                        {
                            "type": "IMAGE",
                            "url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                        }
                    ],
                },
                request_only=True,
            ),
            OpenApiExample(
                "Post sur une page",
                value={
                    "content": "Nouvelle annonce de notre page !",
                    "media": [],
                    "page": "650aaef7-f62d-4763-ab49-115f0036adde",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["📝 Posts"],
        summary="Obtenir un post",
        description="Retourne le détail d'un post par son UUID.",
    ),
    update=extend_schema(
        tags=["📝 Posts"],
        summary="Modifier un post (remplacement complet)",
        description="Met à jour tous les champs d'un post. Réservé à l'auteur.",
    ),
    partial_update=extend_schema(
        tags=["📝 Posts"],
        summary="Modifier un post (partiel)",
        description="Met à jour partiellement un post (PATCH). Réservé à l'auteur.",
    ),
    destroy=extend_schema(
        tags=["📝 Posts"],
        summary="Supprimer un post",
        description="Supprime définitivement un post. Réservé à l'auteur.",
    ),
)

post_mine_schema = extend_schema(
    tags=["📝 Posts"],
    summary="Mes publications",
    description=(
        "Retourne tous les posts créés par l'utilisateur connecté, "
        "qu'ils soient personnels ou publiés sur une de ses pages."
    ),
)

post_like_schema = extend_schema(
    tags=["📝 Posts"],
    summary="Liker un post",
    description=(
        "Ajoute un like de l'utilisateur connecté sur le post. "
        "Idempotent : appeler plusieurs fois ne créé qu'un seul like."
    ),
    responses={200: StatusResponseSchema},
)

post_unlike_schema = extend_schema(
    tags=["📝 Posts"],
    summary="Retirer son like",
    description="Supprime le like de l'utilisateur connecté sur le post.",
    responses={200: StatusResponseSchema},
)

post_share_schema = extend_schema(
    tags=["📝 Posts"],
    summary="Partager un post",
    description="Enregistre un partage du post par l'utilisateur connecté.",
    responses={200: StatusResponseSchema},
)

# ── Pages ─────────────────────────────────────────────────────────────────────
page_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["📄 Pages"],
        summary="Mes pages",
        description=(
            "Retourne uniquement les pages **dont vous êtes propriétaire**. "
            "Pour voir toutes les pages, utilisez la recherche globale."
        ),
    ),
    create=extend_schema(
        tags=["📄 Pages"],
        summary="Créer une page",
        description=(
            "Crée une nouvelle page (marque, entreprise, compte public…). "
            "Vous en devenez automatiquement le propriétaire."
        ),
        examples=[
            OpenApiExample(
                "Créer une page marque",
                value={
                    "name": "Ma Super Boutique",
                    "description": "Vente de produits artisanaux camerounais.",
                    "category": "Commerce",
                    "profile_picture_url": "https://res.cloudinary.com/demo/image/upload/logo.jpg",
                },
                request_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["📄 Pages"],
        summary="Détail d'une page",
        description="Retourne le détail d'une page par son UUID.",
    ),
    update=extend_schema(
        tags=["📄 Pages"],
        summary="Modifier une page",
        description="Modification complète d'une page. Réservé au propriétaire.",
    ),
    partial_update=extend_schema(
        tags=["📄 Pages"],
        summary="Modifier partiellement une page",
        description="Modification partielle (PATCH). Réservé au propriétaire.",
    ),
    destroy=extend_schema(
        tags=["📄 Pages"],
        summary="Supprimer une page",
        description="Supprime définitivement une page. Réservé au propriétaire.",
    ),
)

page_subscribe_schema = extend_schema(
    tags=["📄 Pages"],
    summary="S'abonner à une page",
    description=(
        "Abonne l'utilisateur connecté à la page. "
        "Les posts de la page apparaîtront dans son feed avec un bonus de pertinence (+35). "
        "Idempotent."
    ),
    responses={200: StatusResponseSchema},
)

page_unsubscribe_schema = extend_schema(
    tags=["📄 Pages"],
    summary="Se désabonner d'une page",
    description="Désabonne l'utilisateur connecté de la page.",
    responses={200: StatusResponseSchema},
)

page_posts_schema = extend_schema(
    tags=["📄 Pages"],
    summary="Posts d'une page",
    description="Retourne tous les posts publiés sur une page donnée.",
)

# ── Boosts ────────────────────────────────────────────────────────────────────
boost_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["🚀 Boosts"],
        summary="Mes boosts",
        description=(
            "Retourne tous les boosts créés par l'utilisateur connecté. "
            "Un boost amplifie la visibilité d'un post ou d'une page dans le feed."
        ),
    ),
    create=extend_schema(
        tags=["🚀 Boosts"],
        summary="Créer un boost",
        description=(
            "Crée un nouveau boost en statut **PAUSED**. "
            "Il faut ensuite appeler `/api/boosts/{id}/pay/` pour l'activer.\n\n"
            "**Ciblage d'audience (optionnel)** :\n"
            "- `audience_location` : ville ou région cible\n"
            "- `audience_gender` : `ALL` | `MALE` | `FEMALE`\n"
            "- `audience_age_min` / `audience_age_max` : tranche d'âge\n"
            "- `audience_interests` : liste de centres d'intérêt (ex: `[\"sport\", \"musique\"]`)\n\n"
            "**Poids de classement** calculé automatiquement :\n"
            "- POST → base 100, PAGE → base 50\n"
            "- +1 point par tranche de 10 XAF/USD de budget"
        ),
        examples=[
            OpenApiExample(
                "Booster un post",
                value={
                    "target_type": "POST",
                    "target_id": "04d87a6a-3766-46ec-8e32-c7cae65bb101",
                    "budget": "5000.00",
                    "start_date": "2026-05-06T00:00:00Z",
                    "end_date": "2026-05-13T00:00:00Z",
                    "audience_location": "Douala",
                    "audience_gender": "ALL",
                    "audience_age_min": 18,
                    "audience_age_max": 35,
                    "audience_interests": ["mode", "beauté"],
                },
                request_only=True,
            ),
            OpenApiExample(
                "Booster une page",
                value={
                    "target_type": "PAGE",
                    "target_id": "650aaef7-f62d-4763-ab49-115f0036adde",
                    "budget": "10000.00",
                    "start_date": "2026-05-06T00:00:00Z",
                    "end_date": "2026-05-20T00:00:00Z",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["🚀 Boosts"],
        summary="Détail d'un boost",
        description="Retourne le détail d'un de vos boosts.",
    ),
    update=extend_schema(
        tags=["🚀 Boosts"],
        summary="Modifier un boost",
        description="Modification complète d'un boost.",
    ),
    partial_update=extend_schema(
        tags=["🚀 Boosts"],
        summary="Modifier partiellement un boost",
        description="Modification partielle (PATCH) d'un boost.",
    ),
    destroy=extend_schema(
        tags=["🚀 Boosts"],
        summary="Supprimer un boost",
        description="Supprime un boost définitivement.",
    ),
)

boost_pay_schema = extend_schema(
    tags=["🚀 Boosts"],
    summary="Payer et activer un boost",
    description=(
        "Valide le paiement et passe le boost en statut **ACTIVE**. "
        "Le montant fourni doit être **≥ au budget** défini lors de la création. "
        "Une fois actif, le boost commence à amplifier la visibilité dès que "
        "`start_date` est atteinte."
    ),
    request=PayBoostRequestSchema,
    responses={
        200: PayBoostResponseSchema,
        400: OpenApiResponse(description="Token manquant ou montant insuffisant"),
    },
    examples=[
        OpenApiExample(
            "Payer un boost",
            value={"payment_token": "tok_visa_4242", "amount": "5000.00"},
            request_only=True,
        )
    ],
)

boost_pause_schema = extend_schema(
    tags=["🚀 Boosts"],
    summary="Mettre un boost en pause",
    description=(
        "Suspend temporairement un boost **ACTIVE**. "
        "Le boost n'influence plus le feed pendant la pause. "
        "Utilisez `/resume/` pour le réactiver."
    ),
    responses={
        200: StatusResponseSchema,
        400: OpenApiResponse(description="Le boost n'est pas actif"),
    },
)

boost_resume_schema = extend_schema(
    tags=["🚀 Boosts"],
    summary="Reprendre un boost en pause",
    description="Réactive un boost **PAUSED** et le repasse en statut ACTIVE.",
    responses={
        200: StatusResponseSchema,
        400: OpenApiResponse(description="Le boost n'est pas en pause"),
    },
)

boost_stop_schema = extend_schema(
    tags=["🚀 Boosts"],
    summary="Arrêter définitivement un boost",
    description=(
        "Termine définitivement un boost et positionne `end_date` à maintenant. "
        "Un boost COMPLETED ne peut plus être réactivé."
    ),
    responses={
        200: StatusResponseSchema,
        400: OpenApiResponse(description="Le boost est déjà terminé"),
    },
)

# ── Friendships ───────────────────────────────────────────────────────────────
friendship_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["👥 Amis"],
        summary="Mes demandes d'amitié",
        description=(
            "Retourne toutes les demandes d'amitié impliquant l'utilisateur connecté "
            "(envoyées et reçues), avec leur statut : PENDING, ACCEPTED, DECLINED, BLOCKED."
        ),
    ),
    create=extend_schema(
        tags=["👥 Amis"],
        summary="Envoyer une demande d'amitié",
        description=(
            "Envoie une demande d'amitié à un autre utilisateur. "
            "Si une demande existe déjà (dans un sens ou dans l'autre), "
            "elle est retournée sans en créer une nouvelle."
        ),
        examples=[
            OpenApiExample(
                "Envoyer une demande",
                value={"addressee_id": "650aaef7-f62d-4763-ab49-115f0036adde"},
                request_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["👥 Amis"],
        summary="Détail d'une relation d'amitié",
        description="Retourne le détail d'une relation par son ID.",
    ),
    destroy=extend_schema(
        tags=["👥 Amis"],
        summary="Supprimer / annuler une relation d'amitié",
        description="Supprime la relation d'amitié (annulation, désami, etc.).",
    ),
)

friendship_accept_schema = extend_schema(
    tags=["👥 Amis"],
    summary="Accepter une demande d'amitié",
    description=(
        "Accepte une demande d'amitié reçue. "
        "Seul le destinataire (`addressee`) peut accepter la demande."
    ),
    responses={
        200: StatusResponseSchema,
        403: OpenApiResponse(description="Vous n'êtes pas le destinataire de cette demande"),
    },
)

friendship_decline_schema = extend_schema(
    tags=["👥 Amis"],
    summary="Refuser une demande d'amitié",
    description=(
        "Refuse une demande d'amitié reçue. "
        "Seul le destinataire peut effectuer cette action."
    ),
    responses={
        200: StatusResponseSchema,
        403: OpenApiResponse(description="Action non autorisée"),
    },
)

friendship_suggestions_schema = extend_schema(
    tags=["👥 Amis"],
    summary="Suggestions d'amis",
    description=(
        "Retourne jusqu'à 10 utilisateurs que vous ne connaissez pas encore "
        "(aucune relation d'amitié existante dans aucun sens). "
        "Sélection aléatoire."
    ),
    responses={200: OpenApiResponse(description="Liste de suggestions d'utilisateurs")},
)

# ── Comments ──────────────────────────────────────────────────────────────────
comment_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["💬 Commentaires"],
        summary="Lister les commentaires",
        description=(
            "Retourne les commentaires. Filtrez par post avec le paramètre `?post=<uuid>`.\n\n"
            "Les commentaires sont triés du plus récent au plus ancien."
        ),
        parameters=[
            OpenApiParameter(
                "post",
                OpenApiTypes.UUID,
                OpenApiParameter.QUERY,
                description="Filtrer par UUID du post",
                required=False,
            )
        ],
    ),
    create=extend_schema(
        tags=["💬 Commentaires"],
        summary="Ajouter un commentaire",
        description=(
            "Ajoute un commentaire sur un post. "
            "Pour répondre à un commentaire existant, renseignez `parent_comment` "
            "avec l'UUID du commentaire parent."
        ),
        examples=[
            OpenApiExample(
                "Commentaire simple",
                value={
                    "post": "04d87a6a-3766-46ec-8e32-c7cae65bb101",
                    "content": "Super publication ! 👏",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Réponse à un commentaire",
                value={
                    "post": "04d87a6a-3766-46ec-8e32-c7cae65bb101",
                    "content": "Tout à fait d'accord !",
                    "parent_comment": "c441ad27-26a0-4b8c-a115-afd475fd76e5",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["💬 Commentaires"],
        summary="Détail d'un commentaire",
        description="Retourne un commentaire par son UUID.",
    ),
    update=extend_schema(
        tags=["💬 Commentaires"],
        summary="Modifier un commentaire",
        description="Modification complète d'un commentaire.",
    ),
    partial_update=extend_schema(
        tags=["💬 Commentaires"],
        summary="Modifier partiellement un commentaire",
        description="Modification partielle (PATCH) d'un commentaire.",
    ),
    destroy=extend_schema(
        tags=["💬 Commentaires"],
        summary="Supprimer un commentaire",
        description="Supprime un commentaire définitivement.",
    ),
)

# ── Media Upload ───────────────────────────────────────────────────────────────
upload_schema = extend_schema(
    tags=["📎 Médias"],
    summary="Uploader un fichier (image ou vidéo)",
    description=(
        "Upload un fichier vers **Cloudinary** et retourne son URL publique.\n\n"
        "**Instructions Swagger :**\n"
        "1. Cliquez sur 'Try it out'\n"
        "2. Cliquez sur 'Choisir un fichier' pour importer votre image depuis votre ordinateur.\n"
        "3. Cliquez sur 'Execute'."
    ),
    # C'EST ICI QUE CA SE PASSE :
    request={
        'multipart/form-data': inline_serializer(
            name='InlineUploadSerializer',
            fields={
                'file': serializers.FileField(help_text="L'image ou la vidéo à importer")
            }
        )
    },
    responses={
        201: UploadResponseSchema,
        400: OpenApiResponse(description="Aucun fichier fourni ou format invalide"),
    },
    examples=[
        OpenApiExample(
            "Réponse image uploadée",
            value={
                "url": "https://res.cloudinary.com/myapp/image/upload/v1234/uploads/uuid/photo.jpg",
                "type": "IMAGE",
            },
            response_only=True,
            status_codes=["200"],
        )
    ],
)

# ── Search ────────────────────────────────────────────────────────────────────
search_schema = extend_schema(
    tags=["🔍 Recherche"],
    summary="Recherche globale (utilisateurs + pages)",
    description=(
        "Recherche simultanément dans les **utilisateurs** et les **pages** "
        "selon un terme de recherche.\n\n"
        "La recherche est insensible à la casse et cherche dans :\n"
        "- Utilisateurs : prénom, nom, email\n"
        "- Pages : nom\n\n"
        "Retourne au maximum 10 résultats par catégorie."
    ),
    parameters=[
        OpenApiParameter(
            "q",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            description="Terme de recherche (min. 1 caractère)",
            required=True,
            examples=[
                OpenApiExample("Recherche par prénom", value="Alice"),
                OpenApiExample("Recherche par ville", value="Douala"),
            ],
        )
    ],
    responses={
        200: SearchResponseSchema,
        200: OpenApiResponse(
            description="Résultats de recherche",
            response=SearchResponseSchema,
        ),
    },
)

# ── Health ────────────────────────────────────────────────────────────────────
health_schema = extend_schema(
    tags=["🏥 Santé"],
    summary="Health check",
    description=(
        "Vérifie que l'API est opérationnelle. "
        "Endpoint public, ne requiert pas d'authentification. "
        "Idéal pour les checks de disponibilité (load balancer, monitoring)."
    ),
    auth=[],
    responses={
        200: inline_serializer(
            name="HealthResponse",
            fields={"status": serializers.CharField()},
        )
    },
    examples=[
        OpenApiExample(
            "Réponse OK",
            value={"status": "ok"},
            response_only=True,
            status_codes=["200"],
        )
    ],
)