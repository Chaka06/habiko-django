# Déploiement KIABA Rencontres sur Vercel + Supabase

Ce guide explique comment déployer le projet **KIABA Rencontres** sur Vercel avec Supabase (PostgreSQL + Storage). Le domaine actuel est ci-habiko.com (à remplacer par ci-kiaba.com plus tard si besoin).

## Architecture

- **Code** : GitHub (https://github.com/Chaka06/habiko-django)
- **Hébergement** : Vercel (Python serverless)
- **Base de données** : Supabase PostgreSQL
- **Stockage des images** : Supabase Storage (S3-compatible)
- **Domaine** : ci-habiko.com (via Cloudflare), à migrer vers ci-kiaba.com plus tard

## Prérequis

1. Compte Vercel (https://vercel.com)
2. Compte Supabase (https://supabase.com) — nouveau compte
3. Dépôt GitHub connecté

## Étape 1 : Créer le projet Supabase

1. Va sur https://supabase.com/dashboard
2. Crée un nouveau projet
3. Récupère les informations :
   - **DATABASE_URL** : Settings → Database → Connection string (URI)
   - **Project URL** : Settings → API → Project URL
   - **anon key** : Settings → API → Project API keys

### Supabase Storage (pour les images)

1. Va dans Storage → New bucket
2. Crée un bucket nommé `media` (ou autre)
3. Rends-le public (Public bucket)
4. Active l’API S3-compatible :
   - Settings → Storage → S3 Access Keys
   - Génère Access Key ID et Secret Access Key
   - Endpoint S3 : `https://<project-ref>.supabase.co/storage/v1/s3`

## Étape 2 : Déployer sur Vercel

1. Va sur https://vercel.com/new
2. Importe le dépôt GitHub
3. Framework Preset : Other
4. Variables d’environnement :

```env
# Django
DEBUG=False
SECRET_KEY=<génère une clé sécurisée>
DJANGO_SETTINGS_MODULE=kiaba.settings

# Hosts
ALLOWED_HOSTS=ci-habiko.com,www.ci-habiko.com,.vercel.app
SITE_URL=https://ci-habiko.com

# Base de données Supabase
DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres

# Stockage Supabase (S3-compatible)
USE_SUPABASE_STORAGE=True
SUPABASE_STORAGE_BUCKET=media
SUPABASE_S3_ENDPOINT=https://<project-ref>.supabase.co/storage/v1/s3
SUPABASE_S3_ACCESS_KEY_ID=<access_key_id>
SUPABASE_S3_SECRET_ACCESS_KEY=<secret_access_key>
SUPABASE_STORAGE_PUBLIC_URL=https://<project-ref>.supabase.co/storage/v1/object/public

# Emails - OBLIGATOIRE pour l'inscription (confirmation par email)
# Option 1 - Resend (recommandé, simple, gratuit 3000/mois) : https://resend.com
RESEND_API_KEY=re_xxxxxxxx
DEFAULT_FROM_EMAIL=KIABA Rencontres <onboarding@resend.dev>

# Option 2 - SendGrid : https://sendgrid.com
SENDGRID_API_KEY=SG.xxxxxxxx
DEFAULT_FROM_EMAIL=KIABA Rencontres <no-reply@ci-habiko.com>

# Option 3 - SMTP (Brevo, LWS, etc.)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...

# CinetPay (si utilisé)
CINETPAY_SITE_ID=...
CINETPAY_API_KEY=...
CINETPAY_SITE_KEY=...
```

5. Build Command : `pip install -r requirements.txt && python manage.py collectstatic --noinput --clear`
6. Output Directory : (laisser vide, Vercel utilise les rewrites)
7. Install Command : `pip install -r requirements.txt`

## Étape 3 : Migrations et données initiales

Après le premier déploiement :

1. Vercel Dashboard → Project → Settings → Environment Variables
2. Lance les migrations via Vercel CLI ou un job ponctuel :

```bash
vercel env pull .env.local
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_cities  # Si disponible
python manage.py generate_thumbnails  # Pour les images existantes
```

Ou utilise un script de build personnalisé qui exécute les migrations.

## Étape 4 : Domaine personnalisé

1. Vercel → Project → Settings → Domains
2. Ajoute `ci-habiko.com` et `www.ci-habiko.com`
3. Configure les DNS chez ton registrar ou Cloudflare :
   - CNAME `ci-habiko.com` → `cname.vercel-dns.com`
   - Ou A record vers l’IP Vercel

## Limites Vercel à connaître

- **Taille max du bundle** : 250 Mo (fonctions Python)
- **Cold start** : ~1–3 s au premier appel
- **Durée max d’une requête** : 30 s (Hobby), 60 s (Pro)
- **Stockage** : pas de disque persistant, tout via Supabase Storage

## Troubleshooting

### Erreur CSRF
- Vérifie que `CSRF_TRUSTED_ORIGINS` inclut `https://ci-habiko.com` et `https://*.vercel.app`
- Vérifie que les cookies sont bien envoyés (SameSite, Secure)

### Images non servies
- Vérifie que `USE_SUPABASE_STORAGE=True`
- Vérifie les variables `SUPABASE_S3_*`
- Vérifie que le bucket est public

### Migrations non appliquées
- Exécute les migrations manuellement au premier déploiement
- Ou ajoute un script de post-deploy dans `vercel.json` si supporté

### Pas d'email reçu après inscription
- Configure **RESEND_API_KEY** (recommandé) ou **SENDGRID_API_KEY** dans Vercel → Settings → Environment Variables
- Resend : crée un compte sur https://resend.com, API Keys → Create API Key, colle la clé dans Vercel
- Pour Resend, utilise `onboarding@resend.dev` comme expéditeur (ou vérifie ton domaine)
