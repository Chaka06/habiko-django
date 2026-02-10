# 📧 Système d'Emails KIABA Rencontres

Documentation complète du système d'envoi d'emails automatiques pour la plateforme KIABA Rencontres.

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Types d'emails](#types-demails)
3. [Architecture](#architecture)
4. [Templates](#templates)
5. [Configuration](#configuration)
6. [Tests](#tests)
7. [Dépannage](#dépannage)

---

## 🎯 Vue d'ensemble

Le système d'emails KIABA Rencontres utilise :
- **EmailService** : Service centralisé pour l'envoi d'emails
- **Celery** : Tâches asynchrones avec retry automatique
- **Templates HTML/Texte** : Double format pour compatibilité maximale
- **Logo intégré** : Présent dans header et footer de chaque email

### Caractéristiques

✅ Envoi asynchrone via Celery (retry automatique)  
✅ Templates HTML + Texte pour tous les emails  
✅ Logo KIABA dans chaque email  
✅ Design responsive et professionnel  
✅ Variables dynamiques (site_url, logo_url, support_email)  
✅ Logging complet pour débogage  
✅ Fallback console backend en développement  

---

## 📨 Types d'emails

### 1. **Inscription et Authentification**

#### Email de création de compte
- **Déclencheur** : Inscription d'un nouvel utilisateur
- **Template** : `account_created.html` / `account_created.txt`
- **Tâche** : `send_account_created_email`
- **Contenu** : 
  - Message de bienvenue
  - Lien d'activation du compte
  - Liste des fonctionnalités disponibles

#### Email de confirmation d'email
- **Déclencheur** : Validation de l'adresse email
- **Template** : `email_confirmation.html` / `email_confirmation.txt`
- **Géré par** : django-allauth
- **Contenu** : Lien de confirmation

#### Email de notification de connexion
- **Déclencheur** : Connexion utilisateur
- **Template** : `login_notification.html` / `login_notification.txt`
- **Tâche** : `send_login_notification_email`
- **Contenu** : 
  - Détails de la connexion
  - Lien pour changer le mot de passe
  - Conseils de sécurité

### 2. **Sécurité**

#### Code OTP pour changement de mot de passe
- **Déclencheur** : Demande de changement de mot de passe
- **Template** : `password_change_otp.html` / `password_change_otp.txt`
- **Envoi** : Via view `password_change`
- **Contenu** : 
  - Code de vérification à 5 chiffres
  - Valide 10 minutes
  - Instructions d'utilisation
  - Avertissements de sécurité

#### Confirmation de changement de mot de passe
- **Déclencheur** : Mot de passe modifié avec succès
- **Template** : `password_change.html` / `password_change.txt`
- **Tâche** : `send_password_change_email`
- **Contenu** : 
  - Confirmation du changement
  - Détails (date, heure)
  - Alerte sécurité si non autorisé

### 3. **Gestion des Annonces**

#### Publication d'annonce
- **Déclencheur** : Annonce approuvée et publiée
- **Template** : `ad_published.html` / `ad_published.txt`
- **Tâche** : `send_ad_published_email`
- **Contenu** : 
  - Confirmation de publication
  - Détails de l'annonce (titre, catégorie, ville, expiration)
  - Lien vers l'annonce
  - Conseils pour maximiser la visibilité

#### Expiration d'annonce
- **Déclencheur** : Annonce expirée (14 jours)
- **Template** : `ad_expiration.html` / `ad_expiration.txt`
- **Tâche** : `send_ad_expiration_email`
- **Contenu** : 
  - Notification d'expiration
  - Détails de l'annonce expirée
  - Boutons pour republier ou créer nouvelle annonce
  - Conseil sur la prolongation

#### Annonce approuvée (modération)
- **Déclencheur** : Modérateur approuve une annonce
- **Template** : `ad_approved.html` / `ad_approved.txt`
- **Tâche** : `send_moderation_notification`
- **Contenu** : 
  - Notification d'approbation
  - Détails de l'annonce
  - Lien vers l'annonce
  - Conseils pour booster la visibilité

#### Annonce rejetée (modération)
- **Déclencheur** : Modérateur rejette une annonce
- **Template** : `ad_rejected.html` / `ad_rejected.txt`
- **Tâche** : `send_moderation_notification`
- **Contenu** : 
  - Notification de rejet
  - Raison du rejet
  - Lien vers la politique de contenu
  - Actions recommandées

### 4. **Validation de Profil**

#### Validation de profil
- **Déclencheur** : Mise à jour du profil utilisateur
- **Template** : Texte brut uniquement
- **Tâche** : `send_profile_validation_email`
- **Contenu** : 
  - Lien de validation du profil
  - Informations du profil
  - Liste des avantages

---

## 🏗️ Architecture

### Service EmailService

```python
from accounts.email_service import EmailService

# Envoi simple
EmailService.send_email(
    subject="Mon sujet",
    to_emails=["user@example.com"],
    template_name="account/email/mon_template",
    context={"user": user, "custom_var": "value"},
    fail_silently=False,
)
```

### Tâches Celery

Toutes les tâches d'envoi d'emails sont asynchrones avec retry automatique :

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_ad_published_email(self, ad_id):
    # Code d'envoi
```

**Paramètres de retry** :
- **max_retries** : 5 tentatives
- **countdown** : 60 secondes entre chaque retry
- **retry_backoff** : Augmentation progressive du délai
- **retry_backoff_max** : Maximum 600 secondes (10 minutes)
- **retry_jitter** : Ajoute un délai aléatoire pour éviter les pics

---

## 🎨 Templates

### Structure des templates

Tous les templates héritent de `base_email.html` :

```django
{% extends "account/email/base_email.html" %}

{% block email_title %}Titre de l'email{% endblock %}

{% block email_content %}
    <h1 class="main-title">Mon titre</h1>
    <p>Mon contenu...</p>
{% endblock %}
```

### Variables de contexte disponibles

Automatiquement ajoutées par `EmailService` :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `site_name` | Nom du site | "KIABA Rencontres" |
| `site_url` | URL du site | "https://ci-habiko.com" |
| `support_email` | Email de support | "support@ci-habiko.com" |
| `logo_url` | URL du logo | "https://ci-habiko.com/static/img/logo.png" |
| `user` | Objet utilisateur | `{{ user.username }}` |

### Classes CSS disponibles

Le template de base fournit des classes prêtes à l'emploi :

```css
.main-title          /* Titre principal de l'email */
.info-box            /* Boîte d'information avec fond gris */
.warning-box         /* Boîte d'avertissement jaune */
.security-note       /* Note de sécurité avec bordure rouge */
.details             /* Liste de détails (dl/dt/dd) */
.code-box            /* Boîte pour afficher un code OTP */
.code                /* Code de sécurité (grand, espacé) */
.button              /* Bouton call-to-action jaune */
.button-container    /* Centrage du bouton */
```

### Emojis

Les emojis sont utilisés pour améliorer la lisibilité :

- 🎉 Bienvenue, succès
- 🔐 Sécurité, mot de passe
- ✅ Validation, approbation
- ❌ Rejet, erreur
- ⚠️ Avertissement
- 📧 Email
- 📋 Détails, liste
- 💡 Conseil, astuce
- 🔔 Notification
- ⏰ Expiration, temps

---

## ⚙️ Configuration

### Variables d'environnement

```bash
# Email backend (console pour dev, SMTP pour prod)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# Configuration SMTP (production)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=no-reply@ci-habiko.com
EMAIL_HOST_PASSWORD=your-password

# Expéditeur par défaut
DEFAULT_FROM_EMAIL=KIABA Rencontres <no-reply@ci-habiko.com>
SERVER_EMAIL=KIABA Rencontres Errors <errors@ci-habiko.com>

# Site URL (pour les liens dans les emails)
SITE_URL=https://ci-habiko.com

# Timeout
EMAIL_TIMEOUT=10
```

### Configuration dans `settings.py`

```python
# Email simple (console backend pour développement)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="KIABA Rencontres <no-reply@ci-habiko.com>")
SERVER_EMAIL = env("SERVER_EMAIL", default="KIABA Rencontres Errors <errors@ci-habiko.com>")
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

# Assurer que le nom "KIABA Rencontres" apparaît dans les emails
if not DEFAULT_FROM_EMAIL.startswith("KIABA"):
    if "<" not in DEFAULT_FROM_EMAIL:
        DEFAULT_FROM_EMAIL = f"KIABA Rencontres <{DEFAULT_FROM_EMAIL}>"

EMAIL_USE_LOCALTIME = True
EMAIL_SUBJECT_PREFIX = "[KIABA] "
EMAIL_USE_8BIT = False
EMAIL_CHARSET = "utf-8"
```

---

## 🧪 Tests

### Commande de test

```bash
# Tester tous les templates
python manage.py test_email_templates

# Tester avec un email spécifique
python manage.py test_email_templates --email=test@example.com

# Tester un template spécifique
python manage.py test_email_templates --template=ad_published
```

### Templates disponibles pour test

- `account_created`
- `ad_published`
- `ad_expiration`
- `ad_approved`
- `ad_rejected`
- `password_change`
- `password_change_otp`
- `login_notification`

### Test manuel dans le shell Django

```python
python manage.py shell

from accounts.email_service import EmailService
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

# Test email simple
EmailService.send_email(
    subject="Test email",
    to_emails=["test@example.com"],
    template_name="account/email/account_created",
    context={"user": user},
    fail_silently=False,
)
```

---

## 🔍 Dépannage

### Problème : Les emails ne sont pas envoyés

**Solution 1 : Vérifier le backend email**

```bash
# En développement, les emails s'affichent dans la console
python manage.py runserver

# Vérifier la configuration
python manage.py shell
>>> from django.conf import settings
>>> settings.EMAIL_BACKEND
'django.core.mail.backends.console.EmailBackend'
```

**Solution 2 : Vérifier Celery**

```bash
# Vérifier que Celery tourne
celery -A kiaba worker -l info

# Vérifier les tâches en attente
python manage.py shell
>>> from celery.task.control import inspect
>>> i = inspect()
>>> i.active()
```

**Solution 3 : Logs**

```bash
# Activer les logs détaillés
import logging
logging.basicConfig(level=logging.DEBUG)

# Dans settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'accounts.email_service': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Problème : Le logo ne s'affiche pas

**Cause** : Le logo doit être accessible via une URL publique.

**Solution** :

1. Vérifier que le fichier existe : `static/img/logo.png`
2. Collecter les fichiers statiques : `python manage.py collectstatic`
3. Vérifier `STATIC_URL` et `MEDIA_URL` dans `settings.py`
4. En développement, utiliser `python manage.py runserver` (sert automatiquement les statiques)
5. En production, s'assurer que le serveur web (nginx/apache) sert `/static/`

**Alternative** : Utiliser une URL complète hardcodée

```python
logo_url = "https://ci-habiko.com/static/img/logo.png"
```

### Problème : Templates non trouvés

**Erreur** : `TemplateDoesNotExist: account/email/mon_template.html`

**Solution** :

1. Vérifier que le template existe dans `templates/account/email/`
2. Vérifier `TEMPLATES['DIRS']` dans `settings.py` :

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        ...
    },
]
```

3. Redémarrer le serveur Django

### Problème : Emails en spam

**Solutions** :

1. Configurer SPF/DKIM/DMARC pour votre domaine
2. Utiliser un service d'envoi d'emails professionnel (SendGrid, Mailgun, AWS SES)
3. Éviter les mots-clés spam ("gratuit", "urgent", etc.)
4. Inclure toujours une version texte ET HTML
5. Ajouter un lien de désinscription (pour newsletters)

---

## 📚 Ressources

- [Documentation Django Email](https://docs.djangoproject.com/en/5.1/topics/email/)
- [Documentation Celery](https://docs.celeryq.dev/)
- [django-allauth Email](https://django-allauth.readthedocs.io/en/latest/configuration.html)
- [Best Practices Email HTML](https://www.campaignmonitor.com/css/)

---

## 👨‍💻 Développeur

Système d'emails développé pour **KIABA Rencontres** par Diarrassouba Issiaka Konateh.

📧 Contact : support@ci-habiko.com  
🌐 Site : https://ci-habiko.com

---

**Dernière mise à jour** : Janvier 2026
