# AdSense « Introuvable » – vérifications

Quand AdSense affiche **« Introuvable »** pour ci-kiaba.com (statut « En préparation »), le crawler Google n’a pas pu accéder correctement au site. Voici quoi vérifier.

---

## 1. **ads.txt à la racine** (fait côté projet)

Le fichier **ads.txt** est servi à l’URL :  
**https://ci-kiaba.com/ads.txt**

- Il est généré par la vue `seo.views.ads_txt` avec ton `ADSENSE_PUBLISHER_ID` (variable d’environnement ou défaut en settings).
- Une ligne au format :  
  `google.com, ca-pub-XXXXXXXXXX, DIRECT, f08c47fec0942fa0`  
  est envoyée pour que Google reconnaisse l’inventaire.

**À faire :** Après déploiement, ouvre https://ci-kiaba.com/ads.txt et vérifie que la ligne s’affiche bien (et que le `ca-pub-` correspond à ton compte AdSense).

---

## 2. **Page d’accueil accessible en 200**

AdSense vérifie que la **page d’accueil** répond correctement.

- **URL testée :** https://ci-kiaba.com/ (ou https://ci-kiaba.com)
- **Attendu :** Réponse **HTTP 200** (pas 404, pas 302 vers une page de type « non trouvée »).

**À faire :**

- Ouvrir https://ci-kiaba.com/ en navigation privée (sans cookie).
- Vérifier qu’aucune erreur 404 ni page « Introuvable » ne s’affiche.
- Si tu as un **age gate** (redirection vers /age-gate/) : les bots n’ont pas de cookie ; si la redirection est mal gérée ou que la page de destination renvoie 404, AdSense peut considérer le site comme « Introuvable ». Dans ce cas, soit désactiver l’age gate pour les robots (User-Agent Google), soit s’assurer que la page /age-gate/ renvoie bien 200.

---

## 3. **Vérification AdSense dans l’interface**

Dans **AdSense** (Gestion des sites / Paramètres du site) :

- Vérifier que le **domaine** saisi est bien **ci-kiaba.com** (sans faute, sans sous-domaine inutile).
- Si AdSense propose d’ajouter un **code de vérification** (meta ou fichier) : l’ajouter dans le `<head>` ou exposer le fichier demandé (comme pour Search Console).
- Utiliser **« Vérifier l’URL »** ou **« Tester l’accès »** après chaque correction (ads.txt, homepage, vérification).

---

## 4. **Récap technique côté projet**

| Élément | Statut |
|--------|--------|
| **ads.txt** | Servi via `seo.views.ads_txt` à l’URL `/ads.txt` avec le publisher ID. |
| **Publisher ID** | Variable d’environnement `ADSENSE_PUBLISHER_ID` (défaut : ca-pub-3273662002214639). |
| **Homepage** | `/` → `landing` → contenu liste d’annonces ; doit renvoyer 200. |

Si « Introuvable » persiste après ces vérifications : contrôler les **logs Vercel** au moment où AdSense fait sa requête (erreur 500, timeout, ou blocage par un pare-feu / règle d’accès).
