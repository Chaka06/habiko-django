# Indexation Google Search Console – problèmes et actions

Ce document explique les statuts d’indexation que tu vois dans la Search Console et ce qui est fait ou à faire côté site.

---

## 1. Autre page avec balise canonique correcte (9 pages)

**Signification :** Ces URLs ont une balise canonical qui pointe vers une autre URL. Google ne les indexe pas en tant que pages distinctes (il considère la page canonique comme la version à indexer).

**C’est souvent normal :**
- **Pagination** : `/ads?page=2`, `/ads?page=3`, etc. ont une canonical vers `/ads` (sans `page`) pour éviter le contenu dupliqué. Ces pages ne doivent pas être indexées séparément.
- **Variantes de filtres** : si une URL est considérée comme doublon d’une autre (ex. paramètres inutiles), la canonical est correcte.

**Action :** Aucune en général. Si tu veux que certaines de ces URLs soient indexées (ex. `/ads?city=abidjan`), il faut que leur canonical pointe vers elles-mêmes ; c’est déjà le cas pour les vues liste avec ville/catégorie.

---

## 2. Erreur serveur (5xx) – 6 pages

**Signification :** Google a reçu une réponse 500 (ou 5xx) en explorant ces URLs.

**Ce qui a été fait :**
- **Handler 500** : une vue `server_error_view` renvoie une page HTML propre (template `core/500.html`) avec statut 500 et `noindex, nofollow`, au lieu d’une page d’erreur brute.
- **Templates renforcés** pour éviter les 500 côté rendu :
  - **Liste** (`/ads/`, `/ads/?page=2`) : accès à `ad.media.first.image` uniquement si `media.image` existe ; sinon affichage du placeholder.
  - **Détail annonce** : `contact_prefs` peut être `None` en base → utilisation de `|default:""` pour ne jamais faire `'x' in prefs` sur `None`. Annonces similaires : affichage de l’image uniquement si `similar_ad.media.first` et `first_media.image` existent ; sinon placeholder.
- Ces changements limitent les `AttributeError` / `TypeError` dans les templates (profils sans préférences, médias sans fichier, etc.).

**À faire de ton côté :**
- Consulter les **logs Vercel** (ou les logs de l’app) au moment des 5xx pour identifier la cause (timeout, erreur dans une vue, base de données, etc.).
- Vérifier dans la Search Console quelles URLs exactes renvoient 5xx (rapport « Pages » ou « Couverture ») et les tester à la main.
- Causes fréquentes : timeout serverless, erreur sur une annonce ou une ville inexistante, problème de stockage (images), erreur DB.

---

## 3. Erreur liée à des redirections – 4 pages

**Signification :** Google signale un problème sur des URLs qui redirigent (chaîne de redirections, boucle, ou redirection non suivie correctement).

**Côté site :**
- Redirection **HTTP → HTTPS** (301) en production.
- Pas de redirection www ↔ non-www (désactivée pour éviter les soucis de cookie sur Vercel).
- Les URLs **legal** sont sans slash final (`/legal/tos`, `/legal/privacy`) ; si une requête arrive avec un slash, Django peut rediriger (selon `APPEND_SLASH`).

**À faire :**
- Dans la Search Console, noter les **URLs exactes** concernées par « Erreur liée à des redirections ».
- Tester ces URLs dans le navigateur (et avec un outil type « Redirect Checker ») pour voir la chaîne de redirections.
- Si une URL redirige vers une autre qui elle-même redirige, simplifier (une seule redirection finale vers l’URL canonique).

---

## 4. Bloquée par le fichier robots.txt – 3 pages

**Signification :** Ces URLs correspondent à des chemins interdits dans `robots.txt`.

**Côté site :** Le fichier `robots.txt` (géré par `seo/views.py`) interdit explicitement :
- `/admin/`, `/auth/`, `/accounts/`, `/post/`, `/dashboard/`, `/age-gate/`, `/edit/`, `/report/`

**Conclusion :** C’est **volontaire**. On ne veut pas que Google indexe la connexion, l’inscription, le tableau de bord, les formulaires de dépôt/édition d’annonce, etc. Les 3 pages « bloquées » sont très probablement des URLs de ce type. Aucune action requise sauf si tu souhaites autoriser l’indexation d’un de ces chemins (à éviter pour les pages privées ou formulaire).

---

## 5. Explorée, actuellement non indexée – 3 pages

**Signification :** Google a exploré la page mais a choisi de ne pas l’indexer (priorité faible, contenu jugé fin ou dupliqué, etc.).

**Action :** Pas de correctif technique obligatoire. Tu peux demander une **inspection d’URL** puis « Demander une indexation » pour les pages importantes. Vérifier que le contenu est utile et pas trop proche d’autres pages déjà indexées.

---

## 6. Introuvable (404) – 11 pages

**Signification :** Ces URLs renvoient un code 404 (page introuvable).

**Ce qui a été fait :**
- **Handler 404 global** : toute URL non reconnue par le routeur Django utilise maintenant la vue `page_not_found_view` et le template `core/404.html`, avec **noindex, nofollow** pour que Google ne tente pas d’indexer les erreurs 404.
- Les 404 sont donc des réponses propres (HTML lisible, statut 404).

**À faire :**
- Dans la Search Console, lister les **11 URLs en 404**. Si ce sont d’anciens liens (annonces supprimées, ancienne structure d’URL), c’est normal ; Google finira par les retirer.
- Si ce sont des liens internes ou des URLs que tu veux garder, corriger les liens ou ajouter une redirection 301 vers la bonne URL (ou vers la liste des annonces / accueil).

---

## 7. Page avec redirection – 2 pages (Non commencé)

**Signification :** Ces entrées sont des URLs qui redirigent. Le statut « Non commencé » peut indiquer que Google n’a pas encore vraiment traité l’indexation après la redirection.

**Action :** S’assurer que la redirection est **une seule** redirection (301 ou 302) vers l’URL finale souhaitée. Si les URLs sont correctes (ex. HTTP → HTTPS), rien à changer ; le temps et les réexplorations feront le reste.

---

## Récapitulatif des changements techniques

| Fichier / réglage | Modification |
|-------------------|--------------|
| `templates/base.html` | Bloc `{% block robots %}` pour permettre noindex sur 404/500. |
| `templates/core/404.html` | `{% block robots %}noindex, nofollow{% endblock %}`. |
| `templates/core/500.html` | Nouveau template d’erreur 500 avec noindex, nofollow. |
| `core/views.py` | `page_not_found_view` (404) et `server_error_view` (500). |
| `kiaba/urls.py` | `handler404` et `handler500` pointent vers ces vues. |

Cela améliore la gestion des erreurs côté Google (réponses 404/500 propres, pas d’indexation des pages d’erreur) et donne une base claire pour traiter les 5xx et les 404 listés dans la Search Console.
