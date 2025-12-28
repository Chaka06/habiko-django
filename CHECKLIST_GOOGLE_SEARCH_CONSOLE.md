# 📋 Checklist Google Search Console - Points à Vérifier

## 🔐 Connexion
1. Aller sur https://search.google.com/search-console
2. Se connecter avec ton compte Google
3. Sélectionner la propriété : `https://ci-kiaba.com`

---

## ✅ 1. VÉRIFICATION DE LA PROPRIÉTÉ

### À vérifier :
- [ ] La propriété `https://ci-kiaba.com` est bien ajoutée
- [ ] Le statut de vérification est ✅ "Vérifié"
- [ ] Le fichier de vérification `googleb96ecc9cfd50e4a1.html` est accessible

**Si non vérifié :**
- Aller dans "Paramètres" > "Vérification de la propriété"
- Vérifier que le fichier HTML est accessible : `https://ci-kiaba.com/googleb96ecc9cfd50e4a1.html`

---

## ✅ 2. SITEMAP

### À vérifier :
- [ ] Le sitemap est soumis : `https://ci-kiaba.com/sitemap.xml`
- [ ] Statut : ✅ "Réussi" (pas d'erreur)
- [ ] Nombre d'URLs découvertes : Doit être > 0

**Si erreur :**
- Vérifier que le sitemap est accessible : `https://ci-kiaba.com/sitemap.xml`
- Vérifier qu'il n'y a pas d'erreurs dans le sitemap

**Actions :**
1. Aller dans "Sitemaps" (menu gauche)
2. Vérifier que `sitemap.xml` est listé
3. Si pas présent, cliquer sur "Ajouter un nouveau sitemap"
4. Entrer : `sitemap.xml`
5. Cliquer sur "Envoyer"

---

## ✅ 3. COUVERTURE D'INDEXATION

### À vérifier :
- [ ] Aller dans "Couverture" (menu gauche)
- [ ] Vérifier le nombre d'URLs :
  - ✅ "Valide" : Doit être > 0
  - ❌ "Erreur" : Doit être 0 (ou le moins possible)
  - ⚠️ "Avertissement" : Vérifier chaque cas

### Erreurs courantes à vérifier :

#### ❌ "Page avec redirection"
- **Cause** : Redirection HTTP → HTTPS ou www → non-www
- **Action** : Normal si c'est une redirection 301 vers HTTPS
- **À faire** : Vérifier que la redirection est bien 301 (permanente)

#### ❌ "Page introuvable (404)"
- **Cause** : Liens cassés dans le sitemap
- **Action** : Corriger les URLs dans le sitemap
- **À faire** : Vérifier chaque URL 404 et la corriger

#### ❌ "Page bloquée par robots.txt"
- **Cause** : Page en `Disallow` dans robots.txt
- **Action** : Vérifier robots.txt
- **À faire** : S'assurer que les pages importantes ne sont pas bloquées

#### ❌ "Page avec balise 'noindex'"
- **Cause** : Meta tag `noindex` sur la page
- **Action** : Vérifier les templates
- **À faire** : S'assurer que toutes les pages ont `index, follow`

#### ⚠️ "Découvert - actuellement non indexé"
- **Cause** : Google a trouvé la page mais ne l'a pas encore indexée
- **Action** : Demander l'indexation manuellement
- **À faire** : Utiliser "Inspection d'URL" pour demander l'indexation

---

## ✅ 4. INSPECTION D'URL

### Pages importantes à tester :

1. **Page d'accueil**
   - URL : `https://ci-kiaba.com/`
   - Vérifier :
     - ✅ "Cette URL est sur Google"
     - ✅ "La page est indexée"
     - ✅ "HTTPS" (pas d'erreur)
     - ✅ "Page explorée" (date récente)

2. **Liste des annonces**
   - URL : `https://ci-kiaba.com/ads/`
   - Vérifier : Même chose que ci-dessus

3. **Pages légales**
   - URLs :
     - `https://ci-kiaba.com/legal/tos`
     - `https://ci-kiaba.com/legal/privacy`
     - `https://ci-kiaba.com/legal/content-policy`
   - Vérifier : Même chose

### Actions pour chaque URL :
1. Coller l'URL dans "Inspection d'URL"
2. Cliquer sur "Tester l'URL en direct"
3. Vérifier tous les points ci-dessus
4. Si tout est ✅, cliquer sur "Demander l'indexation"

---

## ✅ 5. PERFORMANCES

### À vérifier :
- [ ] Aller dans "Performances" (menu gauche)
- [ ] Vérifier les métriques :
  - **Impressions** : Nombre de fois que le site apparaît dans les résultats
  - **Clics** : Nombre de clics sur les résultats
  - **CTR** : Taux de clic (Clics / Impressions)
  - **Position moyenne** : Position dans les résultats de recherche

### Si les impressions sont faibles :
- Vérifier que les pages sont bien indexées
- Vérifier que les mots-clés sont présents dans le contenu
- Vérifier que les meta descriptions sont optimisées

---

## ✅ 6. AMÉLIORATIONS ET EXPÉRIENCE

### À vérifier :
- [ ] Aller dans "Améliorations" (menu gauche)
- [ ] Vérifier chaque section :

#### ✅ "HTTPS"
- **Statut** : Doit être ✅ "Toutes les pages utilisent HTTPS"
- **Si erreur** : Vérifier la configuration HTTPS sur Render

#### ✅ "Fils d'Ariane"
- **Statut** : Doit être ✅ "Détecté"
- **Si erreur** : Vérifier que les breadcrumbs sont présents dans les templates

#### ✅ "Liens internes"
- **Statut** : Doit être ✅ "Détecté"
- **Si erreur** : Vérifier que les pages sont bien liées entre elles

#### ✅ "Optimisation mobile"
- **Statut** : Doit être ✅ "Compatible mobile"
- **Si erreur** : Vérifier que le site est responsive

---

## ✅ 7. SÉCURITÉ

### À vérifier :
- [ ] Aller dans "Sécurité et actions manuelles" (menu gauche)
- [ ] Vérifier qu'il n'y a **AUCUNE** action manuelle :
  - ❌ Pas de "Pénalité manuelle"
  - ❌ Pas de "Piratage"
  - ❌ Pas de "Spam"

**Si action manuelle présente :**
- C'est CRITIQUE - Il faut corriger immédiatement
- Suivre les instructions de Google

---

## ✅ 8. LIENS

### À vérifier :
- [ ] Aller dans "Liens" (menu gauche)
- [ ] Vérifier :
  - **Liens externes** : Sites qui pointent vers ton site
  - **Liens internes** : Pages les plus liées
  - **Ancres de liens** : Textes des liens

---

## 📊 RÉSUMÉ - Points Critiques à Me Partager

Après avoir vérifié, partage-moi :

1. **Statut du sitemap** :
   - ✅ Réussi ou ❌ Erreur ?
   - Nombre d'URLs découvertes ?

2. **Couverture d'indexation** :
   - Nombre d'URLs valides ?
   - Nombre d'erreurs ?
   - Quelles erreurs (liste) ?

3. **Inspection d'URL - Page d'accueil** :
   - ✅ Indexée ou ❌ Non indexée ?
   - ✅ HTTPS ou ❌ Pas HTTPS ?
   - Date de dernière exploration ?

4. **Performances** :
   - Nombre d'impressions (derniers 28 jours) ?
   - Nombre de clics ?
   - Position moyenne ?

5. **Améliorations** :
   - ✅ HTTPS : OK ou ❌ Erreur ?
   - ✅ Mobile : OK ou ❌ Erreur ?
   - Autres erreurs ?

6. **Sécurité** :
   - ✅ Aucune action manuelle ou ❌ Problème ?

---

## 🚨 Si Tu Trouves des Erreurs

**Partage-moi :**
1. Le type d'erreur exact
2. L'URL concernée
3. Le message d'erreur complet
4. Une capture d'écran si possible

**Je pourrai alors :**
- Identifier la cause
- Proposer une solution
- Corriger le code si nécessaire

---

## 📝 Notes

- **Délai d'indexation** : Peut prendre 1-7 jours après soumission
- **Mise à jour** : Les changements peuvent prendre 1-3 jours pour apparaître
- **Patience** : L'indexation est un processus continu

---

**Dernière mise à jour :** {{ "now"|date:"d/m/Y" }}

