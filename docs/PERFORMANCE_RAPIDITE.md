# Rapidité du site (post annonce + chargement des pages)

## Comportement : tout apparaît ensemble

Les annonces **n’apparaissent en liste** (et en détail, sitemap, profil public) **que lorsque toutes leurs images sont prêtes** (filigrane + miniature traités). Plus d’affichage intermédiaire « image brute puis miniature » : l’utilisateur ne voit que des annonces complètes.

- Champ **`Ad.image_processing_done`** : à `False` tant qu’au moins une photo est en cours de traitement (tâche Celery) ; passé à `True` quand toutes les photos de l’annonce ont un filigrane et une miniature.
- Liste, détail, sitemap, compteurs, profil public : filtrent sur `status=APPROVED` **et** `image_processing_done=True`.

## Dépôt / édition d’annonce (réponse rapide)

- Les images sont enregistrées en **upload brut** ; le filigrane et la miniature sont traités en **arrière-plan** (tâche Celery `process_ad_media_image`).
- La requête renvoie une redirection en **quelques secondes** au lieu de 15+.
- **Condition** : broker **Redis** (`REDIS_URL`) + worker Celery. Sans Redis, le traitement reste synchrone.
- Variable : `USE_ASYNC_IMAGE_PROCESSING=true` (défaut si Redis est présent).

## Chargement des pages

- **Liste** `/ads` : cache **1 minute** par URL (`@cache_page(60)`).
- **Détail** : cache **2 minutes** par annonce + **une requête** pour les annonces similaires (priorité même ville, puis même catégorie).
- **Index** : `ad_list_ready_idx` sur `(status, image_processing_done)` pour la liste.

## Optimisations ciblées (recommandations)

### Base de données

- **CONN_MAX_AGE = 60** (déjà en place hors Vercel) : réutilisation des connexions PostgreSQL, moins de latence par requête.
- **Pool natif Django 5 + psycopg 3** : si vous utilisez `psycopg[binary,pool]` et Django 5.1+, vous pouvez activer le pool dans `OPTIONS` : `"pool": True`. **Attention** : avec le pool, il faut mettre `CONN_MAX_AGE = 0` (incompatible avec les connexions persistantes). Gain typique : **~5x** sur les requêtes DB (ex. 195 → 1054 req/s dans des benchmarks).
- **Requêtes** : `select_related` / `prefetch_related` déjà utilisés sur liste et détail ; éviter les N+1.

### Cache

- **Redis** : backend de cache (au lieu de LocMem) en production pour partager le cache entre workers et avec Celery.
- **Cache de vues** : liste et détail déjà en `@cache_page` ; adapter les TTL si besoin.

### Réseau et assets

- **GZip** : middleware de compression déjà en place (`GZipCompressionMiddleware`).
- **CDN** : mettre Cloudflare (ou autre) devant le site pour réduire le TTFB et accélérer les assets.
- **Images** : servies par Supabase ; bon cache navigateur via en-têtes.

### Outils

- **django-debug-toolbar** (en dev) : repérer les requêtes lentes et les N+1.
- **Logs SQL lents** : activer `settings.DATABASES["default"]["OPTIONS"]["log_min_duration"]` pour tracer les requêtes > N ms.

## Récap des fichiers concernés

| Fichier | Rôle |
|--------|------|
| `ads/models.py` | `Ad.image_processing_done`, index `ad_list_ready_idx` |
| `ads/tasks.py` | `process_ad_media_image` ; met `image_processing_done=True` quand toutes les photos sont prêtes ; invalide le cache des métriques |
| `core/views.py` | Post / edit : mettent `image_processing_done=False` quand des images sont ajoutées en async |
| `ads/views.py` | Liste, détail, similaires, compteur : filtre `image_processing_done=True` |
| `core/context_processors.py` | Compteur et villes populaires : uniquement annonces prêtes |
| `seo/sitemaps.py` | Sitemap annonces et villes×catégories : uniquement annonces prêtes |
| `accounts/views.py` | Profil public : uniquement annonces prêtes |
