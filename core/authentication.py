import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)

class EmailBackend(ModelBackend):
    """
    Authentifies against settings.AUTH_USER_MODEL.
    The user is looked up by email, but accepts 'username' field containing email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info("\n=== Début de l'authentification ===")
        logger.info(f"Méthode: {request.method if request else 'No request'}")
        logger.info(f"Données brutes: username={username}, password={'*' * len(password) if password else 'None'}")
        
        if not username or not password:
            logger.error("ERREUR: Nom d'utilisateur ou mot de passe manquant")
            return None
            
        try:
            # Normaliser l'email en minuscules
            email = username.lower().strip()
            logger.info(f"Recherche de l'utilisateur avec l'email: {email}")
            
            UserModel = get_user_model()
            logger.info(f"Modèle d'utilisateur: {UserModel.__name__}")
            
            # Vérifier si l'email existe
            user_count = UserModel.objects.filter(email=email).count()
            logger.info(f"Nombre d'utilisateurs trouvés: {user_count}")
            
            user = UserModel.objects.get(email=email)
            logger.info(f"Utilisateur trouvé: ID={user.id}, Email={user.email}, Actif={user.is_active}")
            
            # Vérifier si le compte est actif
            if not user.is_active:
                logger.error("ERREUR: Le compte utilisateur est désactivé")
                return None
                
            # Vérifier le mot de passe
            if user.check_password(password):
                logger.info("SUCCÈS: Authentification réussie")
                return user
            else:
                logger.warning("ÉCHEC: Mot de passe invalide")
                return None
                
        except UserModel.DoesNotExist:
            logger.error(f"ERREUR: Aucun utilisateur trouvé avec l'email: {email}")
            # Vérifier les emails similaires pour le débogage
            similar = UserModel.objects.filter(email__icontains=email.split('@')[0])
            if similar.exists():
                logger.warning(f"Emails similaires trouvés: {[u.email for u in similar]}")
            return None
            
        except Exception as e:
            logger.error(f"ERREUR inattendue: {str(e)}", exc_info=True)
            return None
            
        finally:
            logger.info("=== Fin de l'authentification ===\n")