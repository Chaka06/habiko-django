# ✅ Checklist Google Search Console - HABIKO

## 📋 Vérifications préalables

### 1. Domaine et Configuration
- ✅ **Domaine principal** : `ci-habiko.com`
- ✅ **Domaine avec www** : `www.ci-habiko.com` (redirige vers `ci-habiko.com`)
- ✅ **ALLOWED_HOSTS** : Configuré dans `render.yaml` et `settings.py`
- ✅ **SITE_URL** : `https://ci-habiko.com` (configuré dans Render)
- ✅ **HTTPS** : Activé et forcé via `SECURE_PROXY_SSL_HEADER`

### 2. Fichiers SEO essentiels

#### robots.txt
- ✅ **URL** : `https://ci-habiko.com/robots.txt`
- ✅ **Sitemap référencé** : `https://ci-habiko.com/sitemap.xml`
- ✅ **Permissions** : Toutes les pages publiques autorisées
- ✅ **Disallow** : Admin, auth, dashboard, age-gate correctement bloqués

#### sitemap.xml
- ✅ **URL** : `https://ci-habiko.com/sitemap.xml`
- ✅ **HTTPS forcé** : Oui (via `sitemap_https` view)
- ✅ **Sections incluses** :
  - Pages statiques (accueil, liste annonces, post, pages légales)
  - Toutes les annonces approuvées
  - Toutes les villes
  - Toutes les catégories
  - Combinaisons ville + catégorie
- ✅ **Priorités** : Configurées (1.0 pour accueil, 0.9 pour annonces, etc.)
- ✅ **changefreq** : Configuré (daily pour annonces, weekly pour villes/catégories)

#### Google Verification
- ✅ **Fichier HTML** : `https://ci-habiko.com/googleb96ecc9cfd50e4a1.html`
- ✅ **Meta tag** : Présent dans `base.html` avec le code `uJGTtVemQQT42MBUlLWzHWvX7r3IpCy2iczSO-mXBP0`
- ✅ **Route configurée** : Oui dans `seo/urls.py`

### 3. Structured Data (Schema.org)
- ✅ **WebSite** : Configuré avec SearchAction
- ✅ **Organization** : Configuré avec logo, contact, adresse
- ✅ **LocalBusiness** : Configuré pour Côte d'Ivoire
- ✅ **Product** : Configuré pour chaque annonce (au lieu de Person)
- ✅ **BreadcrumbList** : Configuré sur les pages de détail
- ✅ **ItemList** : Configuré sur la page de liste

### 4. Meta Tags
- ✅ **Title** : Unique et optimisé par page
- ✅ **Description** : Unique, optimisée, 150-160 caractères
- ✅ **Keywords** : Présents (moins important mais présent)
- ✅ **Canonical** : Toutes les pages ont une URL canonique
- ✅ **Open Graph** : Configuré pour Facebook/LinkedIn
- ✅ **Twitter Cards** : Configuré
- ✅ **Hreflang** : Configuré (fr-CI, x-default)

### 5. URLs SEO-friendly
- ✅ **Slugs** : Toutes les annonces utilisent des slugs
- ✅ **HTTPS** : Toutes les URLs en HTTPS
- ✅ **Pas de paramètres inutiles** : URLs propres
- ✅ **Redirection www** : `www.ci-habiko.com` → `ci-habiko.com`

### 6. Performance et Technique
- ✅ **Mobile-friendly** : Responsive design
- ✅ **Vitesse** : Optimisations (lazy loading, compression, cache)
- ✅ **Images** : Alt text optimisés, lazy loading
- ✅ **Liens internes** : Maillage interne présent

## 🚀 Étapes pour Google Search Console

### Étape 1 : Ajouter la propriété
1. Aller sur https://search.google.com/search-console
2. Cliquer sur "Ajouter une propriété"
3. Choisir "Préfixe d'URL"
4. Entrer : `https://ci-habiko.com`
5. Cliquer sur "Continuer"

### Étape 2 : Vérifier la propriété
**Option A : Fichier HTML (Recommandé)**
1. Google va proposer de télécharger un fichier HTML
2. **NE PAS télécharger** - nous avons déjà le fichier configuré
3. Vérifier que `https://ci-habiko.com/googleb96ecc9cfd50e1.html` est accessible
4. Si le code est différent, mettre à jour `seo/views.py` et `templates/base.html`

**Option B : Meta tag (Déjà configuré)**
1. Le meta tag est déjà présent dans `templates/base.html`
2. Code : `uJGTtVemQQT42MBUlLWzHWvX7r3IpCy2iczSO-mXBP0`
3. Cliquer sur "Vérifier"

**Option C : DNS (Si nécessaire)**
1. Si les autres méthodes ne fonctionnent pas
2. Ajouter un enregistrement TXT dans LWS Panel
3. Suivre les instructions de Google

### Étape 3 : Soumettre le sitemap
1. Une fois la propriété vérifiée
2. Aller dans "Sitemaps" dans le menu de gauche
3. Entrer : `sitemap.xml`
4. Cliquer sur "Envoyer"
5. Vérifier que Google trouve toutes les URLs

### Étape 4 : Demander l'indexation
1. Aller dans "Inspection d'URL"
2. Entrer l'URL de la page d'accueil : `https://ci-habiko.com`
3. Cliquer sur "Demander l'indexation"
4. Répéter pour quelques pages importantes :
   - `https://ci-habiko.com/ads`
   - `https://ci-habiko.com/post`
   - Quelques annonces populaires

## 🔍 Vérifications post-soumission

### Après 24-48h, vérifier :
- ✅ **Couverture** : Les pages sont-elles indexées ?
- ✅ **Erreurs** : Y a-t-il des erreurs dans "Couverture" ?
- ✅ **Sitemap** : Le sitemap est-il traité correctement ?
- ✅ **Performance** : Les données de recherche apparaissent-elles ?

## ⚠️ Points d'attention

### Render + LWS
- ✅ Le domaine `ci-habiko.com` est configuré chez LWS
- ✅ Les DNS pointent vers Render
- ✅ Le certificat SSL est valide (géré par Render)
- ✅ Les redirections HTTPS fonctionnent

### Fichiers statiques
- ✅ Les fichiers statiques sont servis correctement
- ✅ Le logo est accessible : `https://ci-habiko.com/static/img/logo.png`
- ✅ Le fichier de vérification Google est accessible

### Middleware
- ✅ `RedirectMiddleware` : Redirige www vers non-www
- ✅ `AgeGateMiddleware` : Bypass pour les robots de recherche
- ✅ `GZipCompressionMiddleware` : Compression activée

## 📊 Métriques à surveiller

Une fois indexé, surveiller dans Google Search Console :
- **Impressions** : Nombre de fois que le site apparaît dans les résultats
- **Clics** : Nombre de clics depuis Google
- **CTR** : Taux de clic (Clics / Impressions)
- **Position moyenne** : Position moyenne dans les résultats
- **Erreurs** : Pages avec erreurs (404, 500, etc.)

## 🎯 Prochaines étapes après indexation

1. **Optimiser le contenu** : Ajouter plus de contenu SEO sur les pages
2. **Backlinks** : Obtenir des liens depuis d'autres sites
3. **Google My Business** : Si applicable, créer un profil
4. **Analytics** : Configurer Google Analytics (si pas déjà fait)
5. **Search Console** : Surveiller régulièrement les performances

## ✅ Statut final

**Tout est prêt pour Google Search Console !**

- ✅ Tous les domaines sont corrects (`ci-habiko.com`)
- ✅ Le sitemap est configuré et accessible
- ✅ Le robots.txt est correct
- ✅ Les structured data sont en place
- ✅ Les meta tags sont optimisés
- ✅ Le fichier de vérification Google est configuré
- ✅ Les URLs sont SEO-friendly
- ✅ Le site est mobile-friendly
- ✅ Les performances sont optimisées

**Tu peux maintenant :**
1. Aller sur Google Search Console
2. Ajouter la propriété `https://ci-habiko.com`
3. Vérifier avec le meta tag (déjà configuré)
4. Soumettre le sitemap `sitemap.xml`
5. Demander l'indexation de la page d'accueil
