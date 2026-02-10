# Configuration SMTP Supabase pour KIABA Rencontres

Ce document explique comment configurer l'envoi d'emails via SMTP Supabase.

## Configuration dans Supabase

1. **Accéder aux paramètres SMTP** :
   - Va sur https://supabase.com/dashboard
   - Sélectionne ton projet
   - Va dans **Settings** → **Auth** → **SMTP Settings**

2. **Configurer un sender email** :
   - Ajoute un email sender (ex: `no-replay@ci-kiaba.com`)
   - Vérifie l'email si nécessaire
   - Récupère les paramètres SMTP fournis par Supabase

## Variables d'environnement nécessaires

Ajoute ces variables dans ton fichier `.env` (local) ou dans Render (production) :

```bash
# Backend email (SMTP Supabase)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# Paramètres SMTP Supabase
EMAIL_HOST=<host_smtp_supabase>          # Ex: mail.smtp.supabase.co ou similaire
EMAIL_PORT=587                            # Port SMTP (587 pour TLS, 465 pour SSL)
EMAIL_HOST_USER=<user_smtp_supabase>      # Utilisateur SMTP fourni par Supabase
EMAIL_HOST_PASSWORD=<password_smtp>       # Mot de passe SMTP fourni par Supabase

# SSL/TLS
EMAIL_USE_SSL=False                       # False pour port 587 (TLS)
EMAIL_USE_TLS=True                        # True pour port 587 (TLS)
# OU
EMAIL_USE_SSL=True                        # True pour port 465 (SSL)
EMAIL_USE_TLS=False                       # False pour port 465 (SSL)

# Identité d'envoi
DEFAULT_FROM_EMAIL=KIABA Rencontres <no-replay@ci-kiaba.com>
SERVER_EMAIL=KIABA Rencontres Errors <no-replay@ci-kiaba.com>

# Timeout (optionnel)
EMAIL_TIMEOUT=10
```

## Exemple de configuration complète

### Pour port 587 (TLS) - Recommandé
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.smtp.supabase.co
EMAIL_PORT=587
EMAIL_HOST_USER=ton-user-supabase
EMAIL_HOST_PASSWORD=ton-password-supabase
EMAIL_USE_SSL=False
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=KIABA Rencontres <no-replay@ci-kiaba.com>
```

### Pour port 465 (SSL)
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.smtp.supabase.co
EMAIL_PORT=465
EMAIL_HOST_USER=ton-user-supabase
EMAIL_HOST_PASSWORD=ton-password-supabase
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
DEFAULT_FROM_EMAIL=KIABA Rencontres <no-replay@ci-kiaba.com>
```

## Configuration sur Render

1. Va sur ton service Render → **Environment**
2. Ajoute toutes les variables d'environnement listées ci-dessus
3. Redéploie le service

## Test de l'envoi d'emails

1. Crée un compte de test sur https://ci-kiaba.com/auth/signup/
2. Vérifie les logs Render pour voir les messages :
   - `📧 Envoi email via SMTP Supabase`
   - `✅ Email envoyé avec succès via SMTP Supabase`

## Dépannage

### Les emails ne sont pas envoyés

1. **Vérifie les logs Render** :
   - Cherche les erreurs SMTP dans les logs
   - Vérifie que `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` sont bien configurés

2. **Vérifie la configuration Supabase** :
   - L'email sender est-il vérifié ?
   - Les paramètres SMTP sont-ils corrects ?

3. **Vérifie les ports** :
   - Port 587 nécessite `EMAIL_USE_TLS=True` et `EMAIL_USE_SSL=False`
   - Port 465 nécessite `EMAIL_USE_SSL=True` et `EMAIL_USE_TLS=False`

### Erreur "Connection refused" ou "Timeout"

- Vérifie que le port est correct (587 ou 465)
- Vérifie que `EMAIL_USE_SSL` et `EMAIL_USE_TLS` correspondent au port utilisé
- Augmente `EMAIL_TIMEOUT` si nécessaire (défaut: 10 secondes)

## Notes importantes

- **En développement local** : Si `EMAIL_HOST` n'est pas configuré, Django utilisera le backend console (emails affichés dans le terminal)
- **Templates d'emails** : Les templates existants dans `templates/account/email/` sont automatiquement utilisés
- **Pas besoin d'API keys** : SMTP Supabase n'utilise pas d'API keys, seulement les identifiants SMTP
