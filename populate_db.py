import os
import random
import uuid
import sys
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile

_START_TIME = time.time()

def _log(msg: str) -> None:
    elapsed = time.time() - _START_TIME
    print(f"[{elapsed:7.1f}s] {msg}", file=sys.stdout, flush=True)

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'boost_backend.settings')
import django
django.setup()

from core.models import User, Page, Post, Like, Comment, Friendship, Boost

# Désactiver les logs de débogage pour le peuplement
import logging
logging.disable(logging.INFO)

# Données de base - Villes du Cameroun
CITIES = [
    'Yaoundé', 'Douala', 'Bamenda', 'Bafoussam', 'Garoua', 'Maroua', 'Ngaoundéré',
    'Kousséri', 'Buea', 'Nkongsamba', 'Bertoua', 'Loum', 'Kumba', 'Edéa', 'Kribi',
    'Limbe', 'Ebolowa', 'Foumban', 'Dschang', 'Bafang', 'Mbouda', 'Eseka', 'Mbalmayo',
    'Meiganga', 'Nkoteng', 'Bafia', 'Wum', 'Kumbo', 'Bangangté', 'Tiko', 'Bafut',
    'Foumbot', 'Yagoua', 'Mokolo', 'Guider', 'Batouri', 'Mora', 'Kaele', 'Tibati', 'Mamfe'
]

# Régions du Cameroun
REGIONS = [
    'Adamaoua', 'Centre', 'Est', 'Extrême-Nord', 'Littoral',
    'Nord', 'Nord-Ouest', 'Ouest', 'Sud', 'Sud-Ouest'
]

COMPANY_TYPES = [
    'Transports', 'Mobilité', 'Voyages', 'Transit', 'Déplacements',
    'Bus Express', 'Transport Interurbain', 'Navettes', 'Lignes',
    'Transport en Commun', 'Transport Routier', 'Transport Urbain',
    'Transport de Marchandises', 'Transport de Personnes', 'Location de Véhicules'
]

COMPANY_NAMES = [
    'Camtrans', 'Camrail', 'Camair', 'Express Union', 'Touristique Express',
    'Amour Mezam', 'Guinness Express', 'Nouvelle Liberté', 'Amour du Voyageur',
    'Sawa Voyages', 'Bensking Express', 'Le Courrier du Sahel', 'ABC Transport',
    'Amour Mezam', 'Bafoussam Express', 'Bamileke Auto', 'Bonaberi Express',
    'Cameroon Travels', 'Central Voyages', 'Chantier Naval', 'Climax', 'Diamond',
    'Efoulan', 'Etoile Filante', 'Express Bafang', 'Express Bafoussam',
    'Express Douala', 'Express Yaoundé', 'Fokou Voyages', 'Guinness Cameroun',
    'Inter-Urbain', 'Jovial', 'Kake Express', 'Kekem Express', 'La Benjamine'
]

# Génération des 30 agences de transport
def get_random_transport_image():
    """Retourne une URL d'image aléatoire liée aux transports au Cameroun"""
    transport_types = [
        'bus', 'taxi', 'moto', 'bush_taxi', 'train', 'bike', 'truck', 'minibus',
        'car_rapide', 'clando', 'bend_skin', 'okada', 'benskin', 'coaster'
    ]
    transport = random.choice(transport_types)
    
    # Utilisation d'Unsplash pour des images libres de droits
    if transport in ['bus', 'taxi', 'train', 'bike', 'truck']:
        return f"https://source.unsplash.com/800x600/?{transport},africa,cameroon"
    
    # Pour les termes spécifiques au Cameroun, on utilise des mots-clés plus généraux
    transport_keywords = {
        'bush_taxi': 'african+bus+transport',
        'minibus': 'minibus+africa',
        'car_rapide': 'african+taxi',
        'clando': 'african+taxi',
        'bend_skin': 'african+motorcycle',
        'okada': 'african+motorcycle+taxi',
        'benskin': 'african+motorcycle',
        'coaster': 'coaster+bus+africa'
    }
    
    return f"https://source.unsplash.com/800x600/?{transport_keywords.get(transport, 'african+transport')}"

def generate_agencies():
    agencies = []
    used_usernames = set()
    used_emails = set()
    
    for i in range(30):
        city = random.choice(CITIES)
        region = random.choice(REGIONS)
        company_type = random.choice(COMPANY_TYPES)
        
        # 70% de chance d'avoir le nom de la ville dans le nom de l'entreprise
        if random.random() < 0.7:
            company_name = f"{random.choice(COMPANY_NAMES)} {company_type} {city}"
        else:
            company_name = f"{random.choice(COMPANY_NAMES)} {company_type} {region}"
            
        base_username = f"{company_name.lower().replace(' ', '_').replace('é','e').replace('è','e')}"
    
        username = base_username
        final_username = username[:30]
        while final_username in used_usernames:
            suffix = str(random.randint(1, 9999))
            candidate = f"{base_username}_{suffix}"
            username = candidate
            final_username = username[:30]
        used_usernames.add(final_username)

        email_domain = random.choice(['gmail.com', 'yahoo.fr', 'hotmail.com', 'outlook.com', 'camnet.cm'])
        email_local = f"contact_{final_username[:15]}"
        email = f"{email_local}@{email_domain}"

        # S'assurer que l'email est unique (sans boucle infinie si le prefix reste identique)
        while email in used_emails:
            email = f"{email_local}{random.randint(1, 9999)}@{email_domain}"
        used_emails.add(email)
        
        agencies.append({
            'username': final_username,  # Limiter la longueur du nom d'utilisateur
            'email': email,
            'company_name': company_name,
            'description': f"Service de transport en commun desservant la ville de {city} et ses alentours. Nous nous engageons à fournir un service de qualité pour tous nos usagers.",
            'city': city,
            'interests': random.sample(
                ['transport', 'mobilité', 'bus', 'taxi', 'moto', 'voyage', 'tourisme', 
                 'développement durable', 'urbain', 'innovation', 'afrique', 'cameroun',
                 'entrepreneuriat', 'technologie', 'logistique', 'commerce', 'import-export',
                 'tourisme local', 'découverte', 'aventure', 'randonnée', 'safari', 'nature'],
                k=random.randint(3, 6)
            )
        })
    
    return agencies

# Génération de 100 utilisateurs clients
def generate_clients():
    # Prénoms courants au Cameroun
    first_names_male = ['Jean', 'Pierre', 'Thomas', 'Nicolas', 'Alexandre', 'François', 'Serge', 'Alain', 'Eric', 'Christian',
                       'Patrice', 'André', 'Michel', 'David', 'Olivier', 'Emmanuel', 'Didier', 'Roger', 'Joseph', 'Jacques',
                       'Paul', 'Daniel', 'Yannick', 'Yves', 'Brice', 'Guy', 'Armel', 'Boris', 'Cédric', 'Désiré',
                       'Ernest', 'Fabrice', 'Gaston', 'Hervé', 'Ivan', 'Joël', 'Kevin', 'Lionel', 'Marc', 'Noël']
    
    first_names_female = ['Marie', 'Sophie', 'Julie', 'Laura', 'Sarah', 'Clara', 'Léa', 'Chloé', 'Inès', 'Emma',
                         'Alice', 'Léna', 'Anna', 'Juliette', 'Charlotte', 'Ambre', 'Amina', 'Béatrice', 'Carine', 'Diane',
                         'Esther', 'Fabiola', 'Grace', 'Hélène', 'Irène', 'Jessica', 'Karen', 'Laure', 'Mariam', 'Nadège',
                         'Olga', 'Prisca', 'Rachel', 'Sandra', 'Tatiana', 'Valérie', 'Yvette', 'Zoe', 'Aïcha', 'Brigitte']
    
    # Noms de famille courants au Cameroun
    last_names = ['Ngo', 'Tchakounte', 'Ndong', 'Mvogo', 'Tchoupo', 'Nkoulou', 'Aboubakar', 'Anguissa', 'Zambo', 'Choupo-Moting',
                 'Ondoua', 'Kunde', 'Nkoudou', 'Toko', 'Nkoulou', 'N\'Jie', 'Bassogog', 'Fai', 'Oyongo', 'Moukandjo',
                 'Ngadeu', 'Castelletto', 'Ondoa', 'Ondoua', 'N\'Jie', 'Aboubakar', 'Nkoulou', 'Anguissa', 'Toko', 'Bassogog',
                 'Nkoudou', 'Ondoua', 'Kunde', 'Ngadeu', 'Oyongo', 'Fai', 'Moukandjo', 'Castelletto', 'Ondoa', 'N\'Jie',
                 'Toko', 'Bassogog', 'Nkoudou', 'Ondoua', 'Kunde', 'Ngadeu', 'Oyongo', 'Fai', 'Moukandjo', 'Castelletto']
    
    clients = []
    used_usernames = set()
    used_emails = set()
    
    for _ in range(100):
        # Choisir un genre et un prénom approprié
        gender = random.choice(['M', 'F'])
        first_name = random.choice(first_names_male if gender == 'M' else first_names_female)
        last_name = random.choice(last_names)
        
        # Créer un nom d'utilisateur unique
        base_username = f"{first_name.lower()}.{last_name.lower()}"
        username = f"{base_username[:25]}{random.randint(1, 99) if random.random() > 0.5 else ''}"
        while username in used_usernames:
            suffix = str(random.randint(1, 9999))
            max_base_len = max(1, 30 - len(suffix))
            username = f"{base_username[:max_base_len]}{suffix}"
        used_usernames.add(username)
        
        # Créer un email avec des domaines camerounais
        email_domains = ['gmail.com', 'yahoo.fr', 'hotmail.com', 'outlook.com', 'yahoo.com', 'live.fr', 'icloud.com']
        email = f"{base_username.replace('.', '')}{random.randint(1, 99)}@{random.choice(email_domains)}"
        
        # S'assurer que l'email est unique
        while email in used_emails:
            email = f"{base_username.replace('.', '')}{random.randint(1, 999)}@{random.choice(email_domains)}"
        used_emails.add(email)
        
        # Centres d'intérêt adaptés au contexte camerounais
        interests_pool = [
            # Transport et mobilité
            'voyage', 'transport', 'mobilité', 'aventure', 'randonnée',
            # Loisirs
            'musique', 'danse', 'cinéma', 'sport', 'football', 'basketball', 'tennis',
            # Culture
            'art', 'culture', 'littérature', 'histoire', 'patrimoine', 'traditions',
            # Technologie
            'technologie', 'informatique', 'réseaux sociaux', 'gaming',
            # Mode et beauté
            'mode', 'beauté', 'coiffure', 'esthétique',
            # Gastronomie
            'cuisine', 'gastronomie', 'restauration', 'pâtisserie',
            # Éducation
            'éducation', 'formation', 'apprentissage', 'langues',
            # Business
            'entrepreneuriat', 'business', 'marketing', 'communication',
            # Santé et bien-être
            'santé', 'bien-être', 'fitness', 'yoga', 'méditation',
            # Nature et environnement
            'nature', 'environnement', 'écologie', 'jardinage',
            # Autres
            'photographie', 'lecture', 'écriture', 'voyages', 'découverte'
        ]
        
        # Ajouter des intérêts spécifiques au Cameroun
        cameroon_specific = ['culture camerounaise', 'musique africaine', 'danse africaine',
                           'cuisine camerounaise', 'tourisme au Cameroun', 'développement du Cameroun']
        
        # Mélanger les intérêts et en sélectionner entre 4 et 8
        all_interests = interests_pool + random.sample(cameroon_specific, min(2, len(cameroon_specific)))
        selected_interests = random.sample(all_interests, k=random.randint(4, 8))
        
        clients.append({
            'first_name': first_name,
            'last_name': last_name,
            'username': username[:30],
            'email': email,
            'city': random.choice(CITIES),
            'gender': gender,
            'birth_date': datetime(1980, 1, 1) + timedelta(days=random.randint(0, 14600)),  # Entre 20 et 60 ans
            'interests': selected_interests
        })
    
    return clients

POST_CONTENTS = [
    {
        'content': 'Découvrez nos nouveaux bus électriques plus écologiques ! 🌱 #transportvert #mobilitédouce',
        'media_type': 'image',
        'media_url': 'https://source.unsplash.com/800x600/?electric+bus,africa'
    },
    {
        'content': 'Voyagez en toute sérénité avec nos services de transport de qualité. #voyage #transport',
        'media_type': 'video',
        'media_url': 'https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4'
    },
    {
        'content': 'Nouvelle ligne de métro ouverte ! Découvrez nos nouveaux itinéraires. #metro #transport',
        'media_type': 'image',
        'media_url': 'https://source.unsplash.com/800x600/?bus+station,africa'
    },
    {
        'content': 'Nos équipes sont à votre service 24/7 pour vous assurer un transport en toute sécurité. #service #transport',
        'media_type': 'image',
        'media_url': 'https://source.unsplash.com/800x600/?bus+driver,africa'
    },
    {
        'content': 'Découvrez notre nouveau service de location de vélos électriques ! #velo #mobilitédouce',
        'media_type': 'video',
        'media_url': 'https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4'
    },
    {
        'content': 'Nos bus sont équipés de la climatisation pour votre confort. #confort #transport',
        'media_type': 'image',
        'media_url': 'https://source.unsplash.com/800x600/?coach+bus,africa'
    },
    {
        'content': 'Nouvelle application mobile disponible ! Gérez vos déplacements en un clic. #appli #mobilite',
        'media_type': 'image',
        'media_url': 'https://source.unsplash.com/800x600/?mobile+app,transport'
    },
    {
        'content': 'Nos chauffeurs sont formés pour assurer votre sécurité. #securite #transport',
        'media_type': 'video',
        'media_url': 'https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4'
    },
    {
        'content': 'Découvrez nos abonnements adaptés à vos besoins. #abonnement #transport',
        'media_type': 'image',
        'media_url': 'https://source.unsplash.com/800x600/?public+transport,ticket'
    },
    {
        'content': 'Nos véhicules sont régulièrement entretenus pour votre sécurité. #entretien #securite',
        'media_type': 'image',
        'media_url': 'https://source.unsplash.com/800x600/?bus+maintenance,garage'
    }
]

def create_users_and_pages():
    # Générer les agences et les clients
    agencies = generate_agencies()
    clients = generate_clients()
    
    users = []
    agency_users = []
    client_users = []
    pages = []
    
    _log("Création des utilisateurs agences...")
    # Création des utilisateurs agences
    for idx, agency in enumerate(agencies, start=1):
        # Création de l'utilisateur agence
        user = User.objects.create_user(
            username=agency['username'],
            email=agency['email'],
            password='password123',  # Mot de passe par défaut
            city=agency['city'],
            interests=agency['interests']
        )
        
        # Utiliser des images d'agences de transport africaines
        user.profile_picture_url = f"https://ui-avatars.com/api/?name={agency['company_name'].replace(' ', '+')}&background=random"
        
        # Utiliser des images de transport en Afrique
        transport_keywords = [
            'african+bus', 'cameroon+transport', 'african+taxi', 'bush+taxi',
            'cameroon+travel', 'africa+transport', 'public+transport+africa'
        ]
        user.cover_photo_url = f"https://source.unsplash.com/random/800x300/?{random.choice(transport_keywords)}"
        
        user.save()
        users.append(user)
        agency_users.append(user)
        
        # Création de la page de l'agence
        page = Page.objects.create(
            owner=user,
            name=agency['company_name'],
            description=agency['description'],
            profile_picture_url=user.profile_picture_url,
            cover_photo_url=user.cover_photo_url,
            category='Transport',
        )
        pages.append(page)

        if idx % 5 == 0 or idx == len(agencies):
            _log(f"Agences: {idx}/{len(agencies)} créées")
    
    _log("Création des utilisateurs clients...")
    # Création des utilisateurs clients
    for idx, client in enumerate(clients, start=1):
        user = User.objects.create_user(
            username=client['username'],
            email=client['email'],
            password='password123',  # Mot de passe par défaut
            first_name=client['first_name'],
            last_name=client['last_name'],
            city=client['city'],
            gender=client['gender'],
            birth_date=client['birth_date'],
            interests=client['interests']
        )
        
        # Utilisation d'une API d'avatars avec des visages africains
        gender_param = 'men' if client['gender'] == 'M' else 'women'
        user.profile_picture_url = f"https://randomuser.me/api/portraits/{gender_param}/{random.randint(1, 99)}.jpg"
        
        # Images de couverture liées au Cameroun
        cameroon_keywords = [
            'cameroon+landscape', 'yaounde+city', 'douala+city', 'mount+cameroon',
            'waza+national+park', 'limbe+beach', 'kribi+beach', 'bamenda+grassfields',
            'foumban+palace', 'dja+faunal+reserve', 'cameroon+culture', 'african+market'
        ]
        user.cover_photo_url = f"https://source.unsplash.com/random/800x300/?{random.choice(cameroon_keywords)}"
        user.save()
        users.append(user)
        client_users.append(user)

        if idx % 20 == 0 or idx == len(clients):
            _log(f"Clients: {idx}/{len(clients)} créés")
    
    return users, agency_users, client_users, pages

def create_posts(agency_users, client_users, pages):
    posts = []
    _log(f"Création des posts (agences={len(agency_users)}, clients={len(client_users)})")
    
    # Créer des posts pour les agences (2-5 par agence)
    for a_idx, agency_user in enumerate(agency_users, start=1):
        agency_pages = Page.objects.filter(owner=agency_user)
        if not agency_pages.exists():
            continue
            
        agency_page = agency_pages.first()
        num_posts = random.randint(2, 5)
        
        for _ in range(num_posts):
            post_data = random.choice(POST_CONTENTS)
            post = Post.objects.create(
                author=agency_user,
                page=agency_page,
                content=post_data['content'],
                media=[{"type": post_data['media_type'].upper(), "url": post_data['media_url']}],
                created_at=timezone.now() - timedelta(days=random.randint(0, 90))
            )
            posts.append(post)

        if a_idx % 5 == 0 or a_idx == len(agency_users):
            _log(f"Posts agences: {a_idx}/{len(agency_users)} auteurs traités (posts={len(posts)})")
    
    # Créer des posts pour les utilisateurs clients (0-3 par utilisateur)
    for c_idx, client_user in enumerate(client_users, start=1):
        num_posts = random.choices([0, 1, 2, 3], weights=[0.3, 0.4, 0.2, 0.1])[0]
        
        for _ in range(num_posts):
            # 70% de chance de poster sur un mur d'agence, 30% sur son propre mur
            if random.random() < 0.7 and pages:
                page = random.choice(pages)
                post_content = random.choice([
                    f"J'ai essayé les services de {page.name}, c'était génial !",
                    f"Je recommande vivement {page.name} pour vos déplacements !",
                    f"Une excellente expérience avec {page.name} aujourd'hui.",
                    f"Merci à {page.name} pour leur service de qualité.",
                    f"J'ai été agréablement surpris par les services de {page.name}."
                ])
                post = Post.objects.create(
                    author=client_user,
                    page=page,
                    content=post_content,
                    media=[],  # Les clients ne peuvent pas ajouter de médias sur les pages d'agence
                    created_at=timezone.now() - timedelta(days=random.randint(0, 90))
                )
            else:
                # Post sur son propre mur
                post_content = random.choice([
                    "Je recherche des recommandations pour un voyage en train.",
                    "Quelqu'un connaît les meilleures lignes de bus pour la ville ?",
                    "Je partage mon expérience de voyage d'aujourd'hui.",
                    "Quelqu'un a déjà essayé le nouveau service de location de vélos ?",
                    "Je cherche un moyen de transport écologique pour me déplacer en ville.",
                    "Avez-vous des astuces pour les déplacements du quotidien ?"
                ])
                post = Post.objects.create(
                    author=client_user,
                    page=None,
                    content=post_content,
                    media=[{"type": random.choice(['IMAGE', 'VIDEO']), "url": f"https://source.unsplash.com/random/800x600/?transport,{random.choice(['bus', 'train', 'bike', 'scooter', 'car'])}"}] if random.random() > 0.5 else [],
                    created_at=timezone.now() - timedelta(days=random.randint(0, 90))
                )
            posts.append(post)

        if c_idx % 20 == 0 or c_idx == len(client_users):
            _log(f"Posts clients: {c_idx}/{len(client_users)} auteurs traités (posts={len(posts)})")
    
    return posts

def create_likes_and_comments(users, posts):
    # Créer des likes
    _log(f"Création des likes & commentaires (users={len(users)}, posts={len(posts)})")
    for p_idx, post in enumerate(posts, start=1):
        likers = random.sample(users, min(10, len(users)))
        for user in likers:
            Like.objects.get_or_create(user=user, post=post)

        if p_idx % 25 == 0 or p_idx == len(posts):
            _log(f"Likes: {p_idx}/{len(posts)} posts traités")
    
    # Créer des commentaires
    for p_idx, post in enumerate(posts, start=1):
        commenters = random.sample(users, min(5, len(users)))
        for user in commenters:
            Comment.objects.create(
                user=user,
                post=post,
                content=random.choice([
                    "Super service !",
                    "J'adore ce nouveau service de transport !",
                    "Très pratique pour mes déplacements quotidiens.",
                    "Je recommande vivement !",
                    "Service de qualité, continuez comme ça !",
                    "Les nouveaux bus sont vraiment confortables.",
                    "Ponctualité au rendez-vous, merci !",
                    "Je suis ravi de cette nouvelle ligne.",
                    "Service client réactif et efficace.",
                    "Je prends ce transport tous les jours, c'est parfait !"
                ]),
                created_at=post.created_at + timedelta(minutes=random.randint(1, 1440))
            )

        if p_idx % 25 == 0 or p_idx == len(posts):
            _log(f"Commentaires: {p_idx}/{len(posts)} posts traités")

def create_friendships(users):
    # Créer des relations d'amitié
    _log(f"Création des relations d'amitié (users={len(users)})")
    for u_idx, user in enumerate(users, start=1):
        # Déterminer le nombre d'amis (entre 5 et 20% des autres utilisateurs)
        num_friends = min(
            max(5, int(len(users) * random.uniform(0.05, 0.2))),  # Entre 5 et 20% des utilisateurs
            len(users) - 1
        )
        
        # Sélectionner des amis aléatoires
        potential_friends = [u for u in users if u != user]
        friends = random.sample(potential_friends, min(num_friends, len(potential_friends)))
        
        for friend in friends:
            # Vérifier si une relation d'amitié existe déjà dans un sens ou dans l'autre
            existing = Friendship.objects.filter(
                (models.Q(requester=user, addressee=friend) | 
                 models.Q(requester=friend, addressee=user))
            ).exists()
            
            if not existing:
                # Créer une relation d'amitié (seulement dans un sens)
                status = 'ACCEPTED' if random.random() > 0.2 else 'PENDING'
                Friendship.objects.create(
                    requester=user,
                    addressee=friend,
                    status=status,
                    created_at=timezone.now() - timedelta(days=random.randint(1, 30))
                )
                
                # Si la demande est acceptée, créer la relation inverse
                if status == 'ACCEPTED' and random.random() > 0.5:
                    Friendship.objects.create(
                        requester=friend,
                        addressee=user,
                        status='ACCEPTED',
                        created_at=timezone.now() - timedelta(days=random.randint(1, 30))
                    )

        if u_idx % 10 == 0 or u_idx == len(users):
            _log(f"Amitiés: {u_idx}/{len(users)} utilisateurs traités")

def create_boosts(users, posts, pages):
    # Créer des boosts pour certaines publications et pages
    for _ in range(20):  # Créer 20 boosts
        user = random.choice(users)
        target_type = random.choice(['POST', 'PAGE'])
        
        if target_type == 'POST':
            target = random.choice(posts)
            target_id = target.id
        else:
            target = random.choice(pages)
            target_id = target.id
        
        start_date = timezone.now() - timedelta(days=random.randint(1, 10))
        end_date = start_date + timedelta(days=random.randint(5, 30))
        
        Boost.objects.create(
            user=user,
            target_id=target_id,
            target_type=target_type,
            budget=random.uniform(50, 500),
            start_date=start_date,
            end_date=end_date,
            status=random.choices(
                ['ACTIVE', 'PAUSED', 'COMPLETED'],
                weights=[0.6, 0.2, 0.2],
                k=1
            )[0],
            audience_location=random.choice(['France', 'Europe', 'Monde']),
            audience_age_min=random.randint(18, 25),
            audience_age_max=random.randint(26, 65),
            audience_gender=random.choice(['M', 'F', None]),
            audience_interests=random.sample(
                ['transport', 'voyage', 'mobilité', 'écologie', 'technologie'],
                k=random.randint(1, 3)
            )
        )

def create_suggestions(users):
    """Créer des suggestions d'amis basées sur des intérêts communs et la localisation."""
    _log("Création des suggestions d'amis...")
    
    for u_idx, user in enumerate(users, start=1):
        # Pour chaque utilisateur, trouver des utilisateurs avec des intérêts similaires
        similar_users = []
        
        # Chercher des utilisateurs avec des intérêts similaires
        if hasattr(user, 'interests') and user.interests:
            for other_user in User.objects.exclude(id=user.id):
                if hasattr(other_user, 'interests') and other_user.interests:
                    # Compter les intérêts communs
                    common_interests = set(user.interests) & set(other_user.interests)
                    if common_interests:
                        # Ajouter un poids pour la même ville
                        city_bonus = 2 if user.city and user.city == other_user.city else 1
                        similar_users.append((other_user, len(common_interests) * city_bonus))
        
        # Trier par similarité et prendre les 10 premiers
        similar_users.sort(key=lambda x: x[1], reverse=True)
        suggested_users = [u[0] for u in similar_users[:10]]
        
        # Ajouter des suggestions aléatoires si nécessaire
        while len(suggested_users) < 10:
            random_user = random.choice([u for u in User.objects.exclude(id=user.id) if u not in suggested_users])
            suggested_users.append(random_user)
            if len(suggested_users) >= 10:
                break
        
        # Stocker les suggestions dans le profil utilisateur (ou dans une table dédiée en production)
        # Ici, on se contente de les afficher
        if u_idx <= 3:
            print(f"\nSuggestions pour {user.username}:")
            for i, suggested in enumerate(suggested_users[:5], 1):
                common = set(getattr(user, 'interests', [])) & set(getattr(suggested, 'interests', []))
                print(f"  {i}. {suggested.username} (Ville: {suggested.city or 'Inconnue'}, Intérêts communs: {len(common)})")

        if u_idx % 20 == 0 or u_idx == len(users):
            _log(f"Suggestions: {u_idx}/{len(users)} utilisateurs traités")

def main():
    _log("Début du peuplement de la base de données...")
    
    # Vider les tables existantes (attention, cette opération est destructrice)
    _log("Vidage des tables existantes...")
    before_users = User.objects.exclude(is_superuser=True).count()
    User.objects.exclude(is_superuser=True).delete()
    after_users = User.objects.exclude(is_superuser=True).count()
    _log(f"Users supprimés (hors superuser): {before_users - after_users}")
    
    # Créer les utilisateurs et les pages
    _log("Création des utilisateurs et des pages...")
    all_users, agency_users, client_users, pages = create_users_and_pages()
    
    # Créer des publications
    _log("Création des publications...")
    posts = create_posts(agency_users, client_users, pages)
    
    # Ajouter des likes et des commentaires
    _log("Ajout des likes et commentaires...")
    create_likes_and_comments(all_users, posts)
    
    # Créer des relations d'amitié
    _log("Création des relations d'amitié et des invitations...")
    create_friendships(all_users)
    
    # Créer des suggestions d'amis
    create_suggestions(client_users)
    
    # Créer des boosts (uniquement pour les agences)
    _log("Création des boosts...")
    create_boosts(agency_users, posts, pages)

    _log("Calcul des statistiques...")
    
    # Statistiques
    print("\n" + "="*50)
    print("PEUPLEMENT TERMINÉ AVEC SUCCÈS !")
    print("="*50)
    print(f"- {len(all_users)} utilisateurs au total")
    print(f"  - {len(agency_users)} comptes agences")
    print(f"  - {len(client_users)} comptes clients")
    print(f"- {len(pages)} pages d'agences créées")
    print(f"- {len(posts)} publications créées")
    print(f"- {Like.objects.count()} likes")
    print(f"- {Comment.objects.count()} commentaires")
    print(f"- {Friendship.objects.count()} relations d'amitié")
    print(f"- {Boost.objects.count()} boosts créés")
    
    # Afficher quelques identifiants de connexion
    print("\nQuelques identifiants de connexion (mot de passe: password123):")
    print("\n--- COMPTES AGENCES ---")
    for user in agency_users[:3]:  # Afficher 3 comptes agences
        print(f"Email: {user.email}")
    
    print("\n--- COMPTES CLIENTS ---")
    for user in client_users[:5]:  # Afficher 5 comptes clients
        print(f"Email: {user.email}")
    
    print("\nPour vous connecter, utilisez l'un des emails ci-dessus avec le mot de passe: password123")

if __name__ == "__main__":
    main()
