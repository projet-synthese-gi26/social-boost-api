import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Page, Post, Boost, TargetType, BoostStatus, PageSubscription, Like, Comment, Share

User = get_user_model()

class Command(BaseCommand):
    help = 'Charge des données de démonstration pour l\'application de transport routier'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Début du chargement des données de transport...'))
        
        # Création des utilisateurs
        admin = User.objects.create_superuser(
            username='admin_transport',
            email='admin@transport.com',
            password='admin123',
            first_name='Admin',
            last_name='Transport'
        )
        
        users = [admin]
        
        # Création de gestionnaires d'agence
        managers = []
        for i in range(1, 4):
            user = User.objects.create_user(
                username=f'manager{i}',
                email=f'manager{i}@transport.com',
                password='manager123',
                first_name=f'Manager {i}',
                last_name='Agence'
            )
            managers.append(user)
            users.append(user)
        
        # Création de chauffeurs
        chauffeurs = []
        noms_chauffeurs = [
            ('Jean', 'Dupont'), ('Pierre', 'Martin'), ('Mohamed', 'Benali'),
            ('Marie', 'Dubois'), ('Sophie', 'Lambert'), ('Thomas', 'Robert'),
            ('Fatima', 'El Mansour'), ('David', 'Simon'), ('Laura', 'Petit'),
            ('Ahmed', 'Khan')
        ]
        
        for i, (prenom, nom) in enumerate(noms_chauffeurs, 1):
            user = User.objects.create_user(
                username=f'chauffeur{i}',
                email=f'chauffeur{i}@transport.com',
                password='chauffeur123',
                first_name=prenom,
                last_name=nom
            )
            chauffeurs.append(user)
            users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'Création de {len(users)} utilisateurs terminée.'))
        
        # Création des pages d'agences de transport
        agences = [
            {
                'name': 'Transports Express',
                'description': 'Service de transport rapide et fiable dans toute la région',
                'category': 'Transport de marchandises',
                'manager': managers[0]
            },
            {
                'name': 'Camions & Cie',
                'description': 'Spécialiste du transport longue distance',
                'category': 'Transport international',
                'manager': managers[1]
            },
            {
                'name': 'Eco-Transports',
                'description': 'Solutions de transport écologiques et durables',
                'category': 'Transport vert',
                'manager': managers[2]
            }
        ]
        
        pages = []
        for agence in agences:
            page = Page.objects.create(
                owner=agence['manager'],
                name=agence['name'],
                description=agence['description'],
                category=agence['category'],
                profile_picture_url='https://example.com/transport-logo.png',
                cover_photo_url='https://example.com/transport-cover.jpg'
            )
            pages.append(page)
            
            # Abonnement du manager à sa page
            PageSubscription.objects.create(user=agence['manager'], page=page)
        
        self.stdout.write(self.style.SUCCESS(f'Création de {len(pages)} pages d\'agences terminée.'))
        
        # Création des publications
        publications = []
        types_transport = ['Camion frigorifique', 'Porte-voitures', 'Plateau', 'Fourgon', 'Camion-citerne']
        villes_depart = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Lille', 'Strasbourg', 'Nantes', 'Toulouse']
        villes_arrivee = ['Berlin', 'Madrid', 'Rome', 'Bruxelles', 'Amsterdam', 'Genève', 'Barcelone', 'Milan']
        
        # Publications des agences
        for page in pages:
            for i in range(5):  # 5 publications par agence
                type_transport = random.choice(types_transport)
                depart = random.choice(villes_depart)
                arrivee = random.choice([v for v in villes_arrivee if v != depart])
                
                post = Post.objects.create(
                    author=page.owner,
                    page=page,
                    content=f"{type_transport} disponible pour un transport de {depart} à {arrivee}. "
                            f"Capacité: {random.randint(1, 30)} tonnes. Contactez-nous pour un devis !",
                    media=[{"type": "IMAGE", "url": f"https://example.com/transport-{random.randint(1, 10)}.jpg"}]
                )
                publications.append(post)
        
        # Publications des chauffeurs
        for chauffeur in chauffeurs[:5]:  # 5 premiers chauffeurs publient
            type_transport = random.choice(types_transport)
            post = Post.objects.create(
                author=chauffeur,
                content=f"Chauffeur {type_transport} disponible pour des missions. "
                        f"Expérience: {random.randint(1, 15)} ans. Permis poids lourd.",
                media=[{"type": "IMAGE", "url": f"https://example.com/driver-{random.randint(1, 5)}.jpg"}]
            )
            publications.append(post)
        
        self.stdout.write(self.style.SUCCESS(f'Création de {len(publications)} publications terminée.'))
        
        # Création des interactions (likes, commentaires, partages)
        for post in publications:
            # Entre 0 et 10 likes par publication
            for user in random.sample(users, random.randint(0, min(10, len(users)))):
                Like.objects.get_or_create(user=user, post=post)
            
            # Entre 0 et 5 commentaires par publication
            for _ in range(random.randint(0, 5)):
                Comment.objects.create(
                    user=random.choice(users),
                    post=post,
                    content=random.choice([
                        "Intéressant ! Je vais vous contacter.",
                        "Quel est le tarif pour 10 tonnes ?",
                        "Disponible la semaine prochaine ?",
                        "Avez-vous des véhicules réfrigérés ?",
                        "Je suis intéressé, contactez-moi en MP.",
                        "Très professionnel, je recommande !"
                    ])
                )
            
            # Entre 0 et 3 partages par publication
            for user in random.sample(users, random.randint(0, min(3, len(users)))):
                Share.objects.create(user=user, post=post)
        
        self.stdout.write(self.style.SUCCESS('Création des interactions terminée.'))
        
        # Création des boosts pour certaines publications (environ 20% des publications)
        for post in random.sample(publications, int(len(publications) * 0.2)):
            start_date = datetime.now() - timedelta(days=random.randint(1, 30))
            end_date = start_date + timedelta(days=random.randint(7, 30))
            
            Boost.objects.create(
                user=post.author,
                target_id=post.id,
                target_type=TargetType.POST,
                budget=random.uniform(50, 500),
                start_date=start_date,
                end_date=end_date,
                status=random.choice([s[0] for s in BoostStatus.choices])
            )
        
        # Boost pour les pages (1 par page)
        for page in pages:
            start_date = datetime.now() - timedelta(days=random.randint(1, 30))
            end_date = start_date + timedelta(days=random.randint(7, 30))
            
            Boost.objects.create(
                user=page.owner,
                target_id=page.id,
                target_type=TargetType.PAGE,
                budget=random.uniform(100, 1000),
                start_date=start_date,
                end_date=end_date,
                status=random.choice([s[0] for s in BoostStatus.choices])
            )
        
        self.stdout.write(self.style.SUCCESS('Création des boosts terminée.'))
        
        self.stdout.write(self.style.SUCCESS('Chargement des données de transport terminé avec succès !'))
        self.stdout.write(self.style.SUCCESS('\nComptes de démonstration :'))
        self.stdout.write(self.style.SUCCESS(f'Admin: email=admin@transport.com, mot de passe=admin123'))
        self.stdout.write(self.style.SUCCESS(f'Manager 1: email=manager1@transport.com, mot de passe=manager123'))
        self.stdout.write(self.style.SUCCESS(f'Chauffeur 1: email=chauffeur1@transport.com, mot de passe=chauffeur123'))
