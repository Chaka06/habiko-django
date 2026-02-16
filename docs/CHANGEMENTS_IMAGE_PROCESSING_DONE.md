# Changements « image_processing_done » – résumé et impacts

## Migration (Supabase = PostgreSQL)

- **Fichier** : `ads/migrations/0010_ad_image_processing_done.py`
- **Effet sur la base** :
  - Ajout de la colonne **`image_processing_done`** (booléen, défaut `True`) sur la table `ads_ad`.
  - Ajout de l’index **`ad_list_ready_idx`** sur `(status, image_processing_done)` pour accélérer la liste d’annonces.

**Exécution au déploiement :**
- **Vercel** : `python manage.py migrate --noinput` est déjà dans la `buildCommand` de `vercel.json` → la migration s’exécute au build.

Aucune action manuelle sur Supabase : Django applique la migration via la connexion existante (`DATABASE_URL`).

---

## Ce qui change dans le code

| Élément | Avant | Après |
|--------|--------|--------|
| **Liste d’annonces** | Toutes les annonces approuvées | Uniquement celles avec `image_processing_done=True` |
| **Détail d’une annonce** | Toute annonce approuvée | Uniquement si `image_processing_done=True` |
| **Compteur « Plus de X annonces »** | Toutes les approuvées | Uniquement les « prêtes » |
| **Villes populaires (footer)** | Comptage sur toutes les approuvées | Comptage sur les « prêtes » |
| **Sitemap** | Toutes les approuvées | Uniquement les « prêtes » |
| **Profil public** | Toutes les annonces de l’utilisateur approuvées | Uniquement les « prêtes » |
| **Nouvelle annonce avec photos (async)** | Visible tout de suite avec images brutes | Visible seulement quand toutes les photos ont filigrane + miniature |

---

## Incidences sur le site

1. **Annonces déjà en base (avant la migration)**  
   La colonne a la valeur par défaut **`True`**. Donc toutes les annonces existantes restent visibles immédiatement, sans changement de comportement.

2. **Nouvelles annonces avec photos (traitement async activé)**  
   - L’annonce est créée et les images sont uploadées en brut.  
   - Elle reste **invisible** (liste, détail, sitemap, compteur, profil) tant que les tâches Celery n’ont pas fini (filigrane + miniature pour chaque photo).  
   - Dès que la dernière tâche a terminé → `image_processing_done` passe à `True` → l’annonce apparaît partout avec toutes les images finales.  
   - **Sans Redis/Celery** : le traitement reste synchrone dans la requête, `image_processing_done` reste `True` dès la création → comportement comme avant (visible tout de suite).

3. **Annonces sans photo**  
   Restent avec `image_processing_done=True` par défaut → visibles tout de suite.

4. **Performance**  
   L’index `ad_list_ready_idx` permet à la liste d’annonces de s’appuyer sur `(status, image_processing_done)` sans dégrader les temps de réponse.

En résumé : pour les annonces déjà en base, rien ne change. Pour les nouvelles avec photos en async, elles n’apparaissent qu’une fois toutes les images traitées (filigrane + miniature).
