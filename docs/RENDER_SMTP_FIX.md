# Solution pour débloquer SMTP sur Render

## Problème identifié

Render bloque les connexions SMTP sortantes pour prévenir le spam :
- **Port 25** : Totalement bloqué
- **Port 465 (SSL)** : Souvent bloqué ou timeout
- **Port 587 (TLS)** : Généralement autorisé ✅

L'erreur `[Errno 101] Network is unreachable` indique que Render bloque la connexion au niveau réseau.

## Solution : Configuration Port 587 avec TLS

### 1. Variables d'environnement sur Render

Modifie ces variables dans Render Dashboard :

```
EMAIL_HOST = mail55.lwspanel.com (ou ton serveur LWS)
EMAIL_PORT = 587  ⚠️ IMPORTANT : Changer de 465 à 587
EMAIL_USE_TLS = True  ⚠️ IMPORTANT : True pour port 587
EMAIL_USE_SSL = False  ⚠️ IMPORTANT : False pour port 587
EMAIL_HOST_USER = no-replay@ci-habiko.com
EMAIL_HOST_PASSWORD = <ton_mot_de_passe_lws>
DEFAULT_FROM_EMAIL = HABIKO <no-replay@ci-habiko.com>
```

### 2. Vérifier que LWS accepte le port 587

1. Va sur ton panneau LWS
2. Vérifie que le port 587 est ouvert pour les connexions externes
3. Certains hébergeurs bloquent les connexions SMTP depuis des IP externes

### 3. Si le port 587 ne fonctionne toujours pas

Le problème peut venir de :
- **L'IP de Render est blacklistée** par LWS
- **LWS bloque les connexions externes** sur SMTP
- **Le serveur SMTP LWS n'accepte pas STARTTLS** correctement

### 4. Alternative : Services SMTP "whitelistés" par Render

Si LWS ne fonctionne pas, utilise un service SMTP qui fonctionne avec Render :

#### Option A : SendGrid SMTP (Gratuit jusqu'à 100 emails/jour)
```
EMAIL_HOST = smtp.sendgrid.net
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = apikey
EMAIL_HOST_PASSWORD = <ton_api_key_sendgrid>
```

#### Option B : Mailgun SMTP (Gratuit jusqu'à 5000 emails/mois)
```
EMAIL_HOST = smtp.mailgun.org
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = <ton_username_mailgun>
EMAIL_HOST_PASSWORD = <ton_password_mailgun>
```

#### Option C : Amazon SES SMTP
```
EMAIL_HOST = email-smtp.<region>.amazonaws.com
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = <aws_access_key>
EMAIL_HOST_PASSWORD = <aws_secret_key>
```

## Test de connexion

Pour tester si la configuration fonctionne :

```python
# Dans Django shell sur Render
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message test', 'no-replay@ci-habiko.com', ['ton-email@gmail.com'], fail_silently=False)
```

## Logs à surveiller

Si ça ne fonctionne pas, vérifie les logs Render pour :
- `ConnectionTimeout` : Le port est bloqué
- `SMTPAuthenticationError` : Problème d'identifiants
- `[Errno 101] Network is unreachable` : Port bloqué par Render
- `[Errno 111] Connection refused` : Serveur SMTP refuse la connexion

## Pourquoi Render bloque SMTP

1. **Anti-spam** : Empêcher les serveurs compromis d'envoyer des spams
2. **Sécurité réseau** : Limiter les connexions sortantes non sécurisées
3. **Réputation IP** : Éviter que les IP de Render soient blacklistées

Les services comme SendGrid/Mailgun sont souvent "whitelistés" car ils utilisent des protocoles sécurisés et ont une bonne réputation.
