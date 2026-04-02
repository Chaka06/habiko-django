"""
Commande de test pour l'envoi d'emails avec templates
Usage: python manage.py test_email_templates
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.email_service import EmailService
from ads.models import Ad
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Teste l'envoi d'emails avec tous les templates disponibles"

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Adresse email de destination pour le test',
        )
        parser.add_argument(
            '--template',
            type=str,
            help='Template spécifique à tester (account_created, ad_published, etc.)',
        )

    def handle(self, *args, **options):
        email = options.get('email')
        template_name = options.get('template')
        
        if not email:
            # Utiliser le premier superuser par défaut
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(self.style.ERROR('❌ Aucun superuser trouvé. Créez-en un d\'abord.'))
                return
            email = user.email
        else:
            # Récupérer ou créer un utilisateur de test
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    username='test_email',
                    email=email,
                    password='testpass123',
                    first_name='Test',
                    last_name='User'
                )
        
        if not email:
            self.stdout.write(self.style.ERROR('❌ Aucune adresse email disponible.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'📧 Email de test : {email}'))
        self.stdout.write(self.style.SUCCESS(f'👤 Utilisateur : {user.username}'))
        self.stdout.write('')
        
        # Liste des templates disponibles
        templates = {
            'account_created': {
                'subject': 'Compte créé avec succès',
                'context': {
                    'user': user,
                    'confirmation_url': f"{settings.SITE_URL}/auth/confirm-email/test-key/",
                }
            },
            'ad_published': {
                'subject': 'Votre annonce est en ligne !',
                'context': {
                    'user': user,
                    'ad': self._get_or_create_test_ad(user),
                    'ad_url': f"{settings.SITE_URL}/ads/test-annonce/",
                }
            },
            'ad_expiration': {
                'subject': 'Votre annonce a expiré',
                'context': {
                    'user': user,
                    'ad': self._get_or_create_test_ad(user),
                    'ad_url': f"{settings.SITE_URL}/ads/test-annonce/",
                }
            },
            'ad_approved': {
                'subject': 'Annonce approuvée',
                'context': {
                    'user': user,
                    'ad': self._get_or_create_test_ad(user),
                    'ad_url': f"{settings.SITE_URL}/ads/test-annonce/",
                }
            },
            'ad_rejected': {
                'subject': 'Annonce rejetée',
                'context': {
                    'user': user,
                    'ad': self._get_or_create_test_ad(user),
                    'ad_url': f"{settings.SITE_URL}/ads/test-annonce/",
                    'reason': 'Contenu non conforme à nos conditions d\'utilisation.',
                }
            },
            'password_change': {
                'subject': 'Mot de passe modifié',
                'context': {
                    'user': user,
                }
            },
            'password_change_otp': {
                'subject': 'Code de vérification',
                'context': {
                    'user': user,
                    'code': '12345',
                }
            },
            'login_notification': {
                'subject': 'Connexion détectée',
                'context': {
                    'user': user,
                }
            },
        }
        
        # Si un template spécifique est demandé
        if template_name:
            if template_name not in templates:
                self.stdout.write(self.style.ERROR(f'❌ Template "{template_name}" introuvable.'))
                self.stdout.write('Templates disponibles : ' + ', '.join(templates.keys()))
                return
            
            templates = {template_name: templates[template_name]}
        
        # Envoyer les emails de test
        self.stdout.write(self.style.WARNING('📤 Envoi des emails de test...\n'))
        
        for name, config in templates.items():
            try:
                success = EmailService.send_email(
                    subject=f"[TEST] {config['subject']}",
                    to_emails=[email],
                    template_name=f"account/email/{name}",
                    context=config['context'],
                    fail_silently=False,
                )
                
                if success:
                    self.stdout.write(self.style.SUCCESS(f'✅ {name}: Envoyé'))
                else:
                    self.stdout.write(self.style.ERROR(f'❌ {name}: Échec'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {name}: Erreur - {str(e)}'))
                logger.exception(f"Erreur envoi template {name}")
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✨ Test terminé !'))
        self.stdout.write(f'📬 Vérifiez l\'email : {email}')
        
        # Afficher la configuration email actuelle
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('⚙️  Configuration email actuelle :'))
        self.stdout.write(f'   Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'   From: {settings.DEFAULT_FROM_EMAIL}')
        if hasattr(settings, 'EMAIL_HOST'):
            self.stdout.write(f'   Host: {settings.EMAIL_HOST}')
            self.stdout.write(f'   Port: {settings.EMAIL_PORT}')
    
    def _get_or_create_test_ad(self, user):
        """Récupère ou crée une annonce de test pour les emails"""
        from ads.models import City
        from django.utils import timezone
        
        # Récupérer ou créer une ville de test
        city = City.objects.first()
        if not city:
            city = City.objects.create(name='Abidjan', slug='abidjan')
        
        # Récupérer ou créer une annonce de test
        ad = Ad.objects.filter(user=user).first()
        if not ad:
            ad = Ad.objects.create(
                user=user,
                title='Belle villa 4 chambres à Cocody',
                description_sanitized='Magnifique villa située dans un quartier calme de Cocody.',
                category=Ad.Category.VILLAS_RESIDENCES,
                subcategories=['Villa de luxe'],
                city=city,
                status=Ad.Status.APPROVED,
                expires_at=timezone.now() + timezone.timedelta(days=14),
            )
        
        return ad
