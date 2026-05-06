"""
Django settings for boost_backend project.
"""

from pathlib import Path
import os
from datetime import timedelta
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SÉCURITÉ ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-^4r=img62q$*x*!mx8#c%%u%ei(#$p$+55a0m3z!0imk0hxagi')

# DEBUG est False par défaut en production. Pour le local, mettez DEBUG=True dans vos variables d'env.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['*']
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# --- CORS CONFIGURATION ---
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://traefikdev.yowyob.com", "https://link-dev.yowyob.com",
]

# Le préfixe de base path géré par Traefik

FORCE_SCRIPT_NAME = os.environ.get("FORCE_SCRIPT_NAME", "")

# Nécessaire pour que les redirects soient corrects
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

FRONTEND_URL = os.environ.get('FRONTEND_URL')
if FRONTEND_URL:
    CORS_ALLOWED_ORIGINS.append(FRONTEND_URL.rstrip("/"))

# Autoriser aussi les previews Vercel (ex: https://monapp-git-branch-xxx.vercel.app)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://traefikdev.yowyob.com", "https://link-dev.yowyob.com",
]
if FRONTEND_URL:
    CSRF_TRUSTED_ORIGINS.append(FRONTEND_URL.rstrip("/"))
CSRF_TRUSTED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type",
    "dnt", "origin", "user-agent", "x-csrftoken", "x-requested-with",
]

# --- APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'cloudinary_storage',  # DOIT ÊTRE EN PREMIER (avant staticfiles)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',  # Pour WhiteNoise
    'django.contrib.staticfiles',
    'cloudinary',                     # Requis pour Cloudinary
    'rest_framework',
    'rest_framework_simplejwt',
    'djoser',
    'drf_spectacular',                # Documentation OpenAPI / Swagger
    'core.apps.CoreConfig',
    'django_filters',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'boost_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'boost_backend.wsgi.application'

# --- BASE DE DONNÉES ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'boost_db'),
        'USER': os.environ.get('POSTGRES_USER', 'lelouch'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'lelouch237'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Override via DATABASE_URL si définie (Neon, Render, etc.)
_db_url = os.environ.get('DATABASE_URL')
if _db_url:
    try:
        db_from_env = dj_database_url.config(conn_max_age=600)
        if db_from_env:
            DATABASES['default'].update(db_from_env)
    except Exception:
        pass  # garder la config par variables séparées

# --- AUTHENTIFICATION ---
AUTH_USER_MODEL = 'core.User'

AUTHENTICATION_BACKENDS = [
    'core.authentication.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# --- REST FRAMEWORK & JWT ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --- drf-spectacular — Swagger / OpenAPI ---
import os

API_BASE_URL = os.environ.get(
    "API_BASE_URL",
    "http://localhost:8000"
)

SPECTACULAR_SETTINGS = {
    'TITLE': 'Boost Social Network API',
    'DESCRIPTION': (
        '## Bienvenue sur la documentation de l\'API Boost Social Network\n\n'
        '### 🔐 Authentification\n'
        'Utilisez `/api/token/` pour obtenir un JWT.\n'
    ),
    'VERSION': '1.0.0',

    # ✅ FIX IMPORTANT : plus de /social-boost injecté automatiquement
    'SERVERS': [
        {
            'url': API_BASE_URL,
            'description': 'Environnement actif (dev / prod)',
        }
    ],

    'SERVE_INCLUDE_SCHEMA': False,

    'SECURITY': [{'BearerAuth': []}],
    'SECURITY_DEFINITIONS': {
        'BearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
    },

    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'docExpansion': 'none',
        'filter': True,
        'tryItOutEnabled': True,
    },

    'COMPONENT_SPLIT_REQUEST': True,
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'core.serializers.MyTokenObtainPairSerializer',
}

DJOSER = {
    'LOGIN_FIELD': 'email',
    'USER_CREATE_PASSWORD_RETYPE': True,
    'PERMISSIONS': {
        'user_create': ['rest_framework.permissions.AllowAny'],
        'user': ['rest_framework.permissions.IsAuthenticated'],
        'user_list': ['rest_framework.permissions.IsAuthenticated'],
        'current_user': ['rest_framework.permissions.IsAuthenticated'],
        'token_create': ['rest_framework.permissions.AllowAny'],
        'token_destroy': ['rest_framework.permissions.IsAuthenticated'],
    },
    'SERIALIZERS': {
        'user_create': 'core.serializers.UserCreateSerializer',
        'user': 'core.serializers.UserSerializer',
        'current_user': 'core.serializers.UserSerializer',
    },
    'JWT_AUTH': {
        'JWT_PAYLOAD_HANDLER': 'rest_framework_simplejwt.utils.jwt_payload_handler',
    }
}

# --- STATICS & MEDIA ---
STATIC_URL = '/social-boost/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configuration Cloudinary
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

# Django 4.2+ : STORAGES remplace DEFAULT_FILE_STORAGE + STATICFILES_STORAGE
# Ne pas définir DEFAULT_FILE_STORAGE ni STATICFILES_STORAGE séparément
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.StaticFilesStorage",
    },
}

WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_USE_FINDERS = True

# --- DIVERS ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}