#!/bin/sh
# ================================================================
# entrypoint.sh — Point d'entrée du conteneur Django
# Gère : attente DB, migrations, collectstatic, démarrage Gunicorn
# ================================================================

set -e

# ── Couleurs pour les logs ───────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()    { echo "${GREEN}[BOOST]${NC} $1"; }
warn()   { echo "${YELLOW}[BOOST]${NC} $1"; }
error()  { echo "${RED}[BOOST]${NC} $1"; }

# ── 1. Vérification des variables Cloudinary ────────────────────
log "Vérification de la configuration Cloudinary..."

if [ -z "$CLOUDINARY_CLOUD_NAME" ] || [ -z "$CLOUDINARY_API_KEY" ] || [ -z "$CLOUDINARY_API_SECRET" ]; then
    warn "⚠️  Variables Cloudinary manquantes ! Les uploads d'images échoueront."
    warn "   Définissez CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET dans votre .env"
else
    log "✅ Cloudinary configuré (cloud: $CLOUDINARY_CLOUD_NAME)"
fi

# ── 2. Attente que PostgreSQL soit prêt ─────────────────────────
log "Attente de PostgreSQL..."

# Extraction des infos de connexion depuis DATABASE_URL ou variables séparées
if [ -n "$DATABASE_URL" ]; then
    # Extraire host et port depuis DATABASE_URL (format: postgres://user:pass@host:port/db)
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/?]*\).*|\1|p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    DB_PORT=${DB_PORT:-5432}
else
    DB_HOST=${POSTGRES_HOST:-db}
    DB_PORT=${POSTGRES_PORT:-5432}
fi

MAX_RETRIES=30
RETRY=0

until python -c "
import sys, psycopg2, os
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL') or
        'host={host} port={port} dbname={db} user={user} password={pwd}'.format(
            host=os.environ.get('POSTGRES_HOST','db'),
            port=os.environ.get('POSTGRES_PORT','5432'),
            db=os.environ.get('POSTGRES_DB','boost_backend_db'),
            user=os.environ.get('POSTGRES_USER','postgres'),
            pwd=os.environ.get('POSTGRES_PASSWORD',''),
        )
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
    RETRY=$((RETRY+1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        error "❌ PostgreSQL n'est pas disponible après $MAX_RETRIES tentatives. Abandon."
        exit 1
    fi
    warn "   PostgreSQL pas encore prêt... tentative $RETRY/$MAX_RETRIES"
    sleep 2
done

log "✅ PostgreSQL est prêt !"

# ── 3. Appliquer les migrations ─────────────────────────────────
log "Application des migrations Django..."
python manage.py migrate --noinput
log "✅ Migrations appliquées !"

# ── 4. Collecte des fichiers statiques ──────────────────────────
log "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear
log "✅ Fichiers statiques collectés !"

# ── 5. (Optionnel) Créer un superuser automatiquement ───────────
# Décommentez et configurez DJANGO_SUPERUSER_* dans .env pour activer
# if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
#     log "Création du superuser Django..."
#     python manage.py createsuperuser --noinput \
#         --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || warn "Superuser existe déjà."
# fi

# ── 6. Lancement de Gunicorn ─────────────────────────────────────
PORT=${PORT:-8000}
WORKERS=${GUNICORN_WORKERS:-2}

log "🚀 Lancement de Gunicorn sur le port $PORT avec $WORKERS workers..."
exec gunicorn boost_backend.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers "$WORKERS" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info