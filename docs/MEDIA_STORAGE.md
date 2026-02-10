# Stockage des images (médias)

**Sur Vercel** : le disque est **en lecture seule** (`/var/task/`). Sans Supabase Storage, les photos des annonces **ne peuvent pas être enregistrées** (erreur `Read-only file system`). Il faut **obligatoirement** configurer Supabase Storage (voir ci‑dessous).

Pour que **les images ne se perdent pas au déploiement** (Render, etc.), stocker les fichiers dans un espace persistant (Supabase Storage ou S3), et non sur le disque local.

## Comportement

- **En base de données** : le champ `image` des annonces enregistre le **chemin** du fichier (ex. `ads/abc123.webp`).
- **Fichier réel** : stocké soit sur le disque du serveur (perdu au redéploiement), soit dans un **bucket Supabase** (persistant).

## Activer le stockage persistant (Supabase Storage)

1. Créer un bucket **public** dans Supabase : Dashboard → Storage → New bucket (ex. `media`).
2. Récupérer les identifiants S3-compatibles Supabase (Storage → Configuration ou docs Supabase).
3. Définir les variables d’environnement suivantes (Render, Vercel, etc.) :

```bash
USE_SUPABASE_STORAGE=true
SUPABASE_S3_ACCESS_KEY_ID=...
SUPABASE_S3_SECRET_ACCESS_KEY=...
SUPABASE_STORAGE_BUCKET=media
SUPABASE_S3_ENDPOINT=https://xxx.supabase.co/storage/v1/s3
# Optionnel : domaine public pour les URLs des images
SUPABASE_STORAGE_PUBLIC_URL=xxx.supabase.co
```

4. Redéployer. Les nouvelles images seront enregistrées dans le bucket ; le **lien** (chemin) reste en base, le **fichier** est dans Supabase.

**Vercel** : si `SUPABASE_S3_ENDPOINT` (et les autres variables Supabase S3) sont définis, le projet active automatiquement le stockage Supabase même sans `USE_SUPABASE_STORAGE=true`, car le disque est en lecture seule.

## Optimisation des images

À l’upload, les images sont automatiquement :

- Redimensionnées (max 1000×1000 px)
- Converties en WebP (qualité 65) ou JPEG (qualité 65) en secours
- Une miniature (320×320) est générée pour les listes

Les fichiers servis sont donc plus légers et le chemin en base pointe vers cette version optimisée.
