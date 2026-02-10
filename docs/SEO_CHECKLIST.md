# Checklist SEO – KIABA Rencontres (ci-kiaba.com)

## 1. Robots et crawl

- **robots.txt** : `https://ci-kiaba.com/robots.txt`
  - `User-agent: *` puis `Allow: /`, `Allow: /ads`, `Allow: /ads/`, `Allow: /legal/`, etc.
  - `Disallow` : `/admin/`, `/auth/`, `/accounts/`, `/post/`, `/dashboard/`, `/age-gate/`, `/edit/`, `/report/`
  - `Sitemap: https://ci-kiaba.com/sitemap.xml`
- **Age gate** : la modale 18+ est gérée en JavaScript (sessionStorage). Les robots reçoivent le HTML complet (sans exécution JS) et peuvent suivre tous les liens. Aucune redirection ne bloque les crawlers.
- **Pas de Crawl-delay** : Google l’ignore ; il a été retiré pour rester conforme aux bonnes pratiques.

## 2. Sitemap

- **URL** : `https://ci-kiaba.com/sitemap.xml`
- **Contenu** : index qui pointe vers les sections suivantes :
  - **static** : `/`, `/ads`, `/post`, `/legal/tos`, `/legal/privacy`, `/legal/content-policy`
  - **ads** : toutes les annonces approuvées (`/ads/<slug>/`)
  - **cities** : `/ads?city=<slug>` pour chaque ville
  - **categories** : `/ads?category=escorte_girl`, `escorte_boy`, `transgenre`
  - **city_categories** : `/ads?city=<slug>&category=<cat>` pour les combinaisons ville × catégorie ayant des annonces
- **Limites** : `AdSitemap` et `CityCategorySitemap` limités à 5000 URLs par section (Google accepte jusqu’à 50 000).
- **HTTPS** : la vue `sitemap_https` force le schéma HTTPS pour toutes les URLs du sitemap.

## 3. Balises et métadonnées (base.html)

- **Title** : bloc `{% block title %}` (défaut : « KIABA · Rencontres & Annonces Adultes »).
- **Meta description** : bloc `{% block description %}`.
- **Meta keywords** : bloc `{% block keywords %}`.
- **Canonical** : `{% block canonical_url %}` (défaut : `https://ci-kiaba.com`).
- **Robots** : `index, follow` par défaut ; pages privées (login, signup, dashboard, etc.) : `noindex, nofollow` dans leur template.
- **Open Graph** : og:type, og:url, og:title, og:description, og:image, og:site_name, og:locale.
- **Twitter** : twitter:card, url, title, description, image.
- **Hreflang** : fr-CI et x-default vers ci-kiaba.com.
- **Geo** : meta geo.region (CI), geo.country, geo.placename (Abidjan).
- **Google Search Console** : meta `google-site-verification` (valeur dans base.html).

## 4. Pages à ne pas indexer (noindex)

Déjà en place dans les templates concernés :

- `/auth/login/`, `/auth/signup/`
- `/dashboard/`
- `/age-gate/` (page dédiée si utilisée)
- Formulaires sensibles (edit, post, etc. selon besoin)

## 5. Google Search Console

1. Vérifier la propriété avec le fichier ou la meta tag déjà en place.
2. Soumettre le sitemap : **https://ci-kiaba.com/sitemap.xml**
3. Vérifier « Couverture » et « Exploration » après quelques jours.
4. Pas d’URL de test avec `Crawl-delay` ou blocage des robots sur les pages publiques.

## 6. Vérification rapide

- Ouvrir `https://ci-kiaba.com/robots.txt` : doit afficher Allow/Disallow et Sitemap.
- Ouvrir `https://ci-kiaba.com/sitemap.xml` : doit afficher un index XML avec des `<sitemap>` ou des `<url>`.
- Tester une URL d’annonce : `https://ci-kiaba.com/ads/<slug>` doit retourner 200 et du HTML avec title/description/canonical.
- Outil « Test d’affichage des résultats de recherche » (Search Console) : vérifier titre, meta description et canonical.

## 7. Fichiers concernés dans le projet

- `seo/views.py` : `robots_txt`
- `seo/sitemaps.py` : `StaticSitemap`, `AdSitemap`, `CitySitemap`, `CategorySitemap`, `CityCategorySitemap`
- `kiaba/urls.py` : route `sitemap.xml` → `sitemap_https`
- `templates/base.html` : meta tags, canonical, OG, Twitter
- Pages spécifiques : `ads/list.html`, `ads/detail.html`, `core/home.html`, etc. : surcharge des blocs title, description, canonical quand nécessaire.
