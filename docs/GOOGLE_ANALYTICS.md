# Google Analytics 4 (GA4) – KIABA Rencontres

L’intégration GA4 est déjà en place dans le site. Il suffit de créer une propriété et de renseigner l’ID de mesure.

## 1. Créer une propriété GA4

1. Va sur [Google Analytics](https://analytics.google.com/).
2. Connecte-toi avec le compte Google à utiliser pour les stats.
3. **Admin** (engrenage en bas à gauche) → **Créer une propriété**.
4. Nom de la propriété : par ex. **KIABA Rencontres**.
5. Fuseau horaire : **Abidjan (UTC+0)** (ou celui de ton choix).
6. Devise : **XOF** ou **EUR**.
7. Valide la création.
8. Choisis **Plateforme Web** → URL : `https://ci-kiaba.com` → Nom du flux : **ci-kiaba.com**.
9. Une fois le flux créé, tu obtiens un **ID de mesure** au format **G-XXXXXXXXXX**.

## 2. Où configurer l’ID

- **En local** : dans ton fichier `.env` à la racine du projet :
  ```env
  GA_MEASUREMENT_ID=G-XXXXXXXXXX
  ```
- **En production** (Render / Vercel / autre) : ajoute la variable d’environnement **GA_MEASUREMENT_ID** avec la valeur `G-XXXXXXXXXX` dans le tableau de bord (Environment / Variables d’environnement).

## 3. Comportement sur le site

- Le script Google Analytics ne se charge **que si l’utilisateur accepte les cookies “Analytics”** dans le bandeau de consentement.
- Si `GA_MEASUREMENT_ID` est vide ou absent, aucun script GA n’est chargé.
- Les pages sont suivies automatiquement (page_view). L’IP est anonymisée (`anonymize_ip: true`).

## 4. Vérifier que ça fonctionne

1. Déploie ou lance le site avec `GA_MEASUREMENT_ID` défini.
2. Accepte les cookies analytics sur le site.
3. Dans GA4 : **Rapports** → **Temps réel** ; tu devrais voir ta visite après quelques secondes.

## Référence technique

- **Settings** : `kiaba/settings.py` → `GA_MEASUREMENT_ID`
- **Contexte template** : `core/context_processors.py` → `GA_MEASUREMENT_ID`
- **Template** : `templates/base.html` (bloc « Google Analytics - Respect du consentement »)
