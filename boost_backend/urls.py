"""
URL configuration for boost_backend project.

Documentation Swagger :
  - Interface Swagger UI : /api/docs/
  - Interface ReDoc      : /api/redoc/
  - Schéma OpenAPI brut  : /api/schema/
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from core.views import MyTokenObtainPairView
from core.swagger_extensions import token_refresh_schema, health_schema

# Décorer les vues externes avec leurs schémas Swagger
TokenRefreshView = token_refresh_schema(TokenRefreshView)

def health_view(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    # ── Admin Django ───────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Authentification (Djoser + JWT) ───────────────────────────────────
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── API Core (posts, pages, boosts, users, etc.) ──────────────────────
    path('api/', include('core.urls')),

    # ── Health Check ───────────────────────────────────────────────────────
    path('api/health/', health_schema(health_view), name='health_check'),

    # ── Documentation OpenAPI ─────────────────────────────────────────────
    # Schéma brut JSON/YAML (utilisé par Swagger UI et ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI  →  http://localhost:8000/api/docs/
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),

    # ReDoc (documentation lisible)  →  http://localhost:8000/api/redoc/
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
