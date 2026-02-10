# Guide pas à pas : Connexion / inscription avec Google

Suivez ces étapes dans l’ordre. À la fin, le bouton « Continuer avec Google » et « S'inscrire avec Google » fonctionneront sur le site.

---

## Tout faire sur Vercel (sans rien lancer en local)

Si tu déploies uniquement sur Vercel et ne veux rien faire en local :

1. **Google Cloud Console** : crée l’ID client OAuth (Application Web) et les deux URI de redirection (voir Étape 1 ci-dessous). Note l’**ID client** et le **Secret client**.
2. **Vercel** : va sur ton projet → **Settings** → **Environment Variables**. Ajoute :
   - `GOOGLE_OAUTH_CLIENT_ID` = ton ID client
   - `GOOGLE_OAUTH_CLIENT_SECRET` = ton secret client  
   Coche **Production** (et **Preview** si tu veux), puis **Save**.
3. **Déploiement** : pousse ton code sur Git (ou déclenche un déploiement depuis le dashboard Vercel). Le build exécute automatiquement `python manage.py migrate`, donc les tables Google (socialaccount) sont créées à chaque déploiement. Aucune commande à lancer en local.
4. **Test** : va sur **https://ci-kiaba.com/auth/login/** et clique sur « Continuer avec Google ».

---

## Étape 1 : Créer un projet et les identifiants dans Google Cloud Console

### 1.1 Ouvrir la console

1. Va sur **https://console.cloud.google.com/**
2. Connecte-toi avec ton compte Google.

### 1.2 Créer ou choisir un projet

- En haut de la page, clique sur le **sélecteur de projet** (à côté de « Google Cloud »).
- Soit tu **choisis un projet existant**, soit tu cliques sur **« Nouveau projet »** :
  - Nom du projet : par ex. `KIABA` ou `ci-kiaba`
  - Clique sur **« Créer »**
- Sélectionne ce projet pour qu’il soit actif (affiché en haut).

### 1.3 Activer l’écran de consentement OAuth (si demandé)

- Dans le menu de gauche (☰), va dans **« APIs et services »** → **« Écran de consentement OAuth »**.
- Si tu n’as rien configuré :
  - Type d’utilisateur : **Externe** (pour que n’importe quel compte Google puisse se connecter).
  - Clique sur **« Créer »**.
  - Renseigne au minimum : **Nom de l’application** (ex. `KIABA Rencontres`), **E-mail d’assistance utilisateur** (ton email), **Domaine** (optionnel : `ci-kiaba.com`).
  - Clique sur **« Enregistrer et continuer »** jusqu’à la fin (tu peux ignorer les étapes optionnelles en cliquant sur « Enregistrer et continuer »).

### 1.4 Créer les identifiants OAuth

1. Menu de gauche : **« APIs et services »** → **「 Identifiants 」**.
2. Clique sur **「 + Créer des identifiants 」** (en haut).
3. Choisis **「 ID client OAuth 」**.
4. **Type d’application** : sélectionne **「 Application Web 」**.
5. **Nom** : laisse par défaut (ex. « Client Web 1 ») ou mets « KIABA Web ».
6. **URI de redirection autorisés** :
   - Clique sur **「 + AJOUTER UN URI 」**.
   - Ajoute **exactement** (copier-coller) :
     - `https://ci-kiaba.com/auth/google/login/callback/`
   - Clique à nouveau sur **「 + AJOUTER UN URI 」** et ajoute :
     - `http://localhost:8000/auth/google/login/callback/`
7. Clique sur **「 Créer 」**.

### 1.5 Récupérer l’ID client et le secret

- Une fenêtre s’affiche avec :
  - **ID client** : une longue chaîne se terminant par `….apps.googleusercontent.com`
  - **Secret client** : une chaîne du type `GOCSPX-…`
- **Garde cette fenêtre ouverte** (ou note les deux valeurs) : tu en auras besoin à l’étape 2.
- Tu peux aussi les retrouver plus tard : **APIs et services** → **Identifiants** → clique sur le nom de ton « ID client OAuth » (Client Web 1 ou KIABA Web).

---

## Étape 2 : Renseigner les variables d’environnement

### 2.1 En local (fichier `.env`)

1. Ouvre le fichier **`.env`** à la racine du projet (à côté de `manage.py`).
2. Si les lignes existent déjà avec des valeurs vides, remplace-les. Sinon, ajoute :

```bash
GOOGLE_OAUTH_CLIENT_ID=ton_id_client_ici.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-ton_secret_ici
```

- Remplace `ton_id_client_ici.apps.googleusercontent.com` par l’**ID client** copié à l’étape 1.5.
- Remplace `GOCSPX-ton_secret_ici` par le **Secret client**.
- Pas d’espaces autour du `=`, pas de guillemets sauf si ton éditeur en exige.

3. Enregistre le fichier.

### 2.2 En production (Vercel)

1. Va sur **https://vercel.com/** → ton projet (ex. habiko-django ou ci-kiaba).
2. Onglet **「 Settings 」** → **「 Environment Variables 」**.
3. Ajoute deux variables :
   - **Name** : `GOOGLE_OAUTH_CLIENT_ID`  
     **Value** : ton ID client (le même qu’en local).  
     Coche **Production** (et **Preview** si tu veux aussi sur les previews).
   - **Name** : `GOOGLE_OAUTH_CLIENT_SECRET`  
     **Value** : ton secret client.  
     Coche **Production** (et **Preview** si besoin).
4. Clique sur **「 Save 」**.
5. **Redéploie** le projet (Deployments → … sur le dernier déploiement → **Redeploy**) pour que les nouvelles variables soient prises en compte.

---

## Étape 3 : Lancer les migrations (tables socialaccount)

1. Ouvre un terminal dans le dossier du projet.
2. **Active l’environnement virtuel** (obligatoire) :
   - Si ton venv est dans le projet :  
     `source venv/bin/activate` (Mac/Linux) ou `venv\Scripts\activate` (Windows).
   - Ou selon ta config : `source .venv/bin/activate`, etc.
3. Lance les migrations :

```bash
python manage.py migrate
```

4. Tu dois voir des lignes du type « Applying socialaccount.0001_initial… OK » (ou numéros différents). Pas d’erreur = c’est bon.

---

## Étape 4 : Vérifier que ça marche

### En local

1. Démarre le serveur : `python manage.py runserver`
2. Va sur **http://localhost:8000/auth/login/** (ou la page d’inscription).
3. Clique sur **「 Continuer avec Google 」** ou **「 S'inscrire avec Google 」**.
4. Tu dois être redirigé vers Google, puis revenir sur le site connecté (ou inscrit).

### En production (ci-kiaba.com)

1. Après le redéploiement Vercel, va sur **https://ci-kiaba.com/auth/login/**.
2. Clique sur **「 Continuer avec Google 」**.
3. Même flux : Google puis retour sur le site connecté.

---

## En cas de problème

| Problème | Solution |
|----------|----------|
| **« redirect_uri_mismatch »** | Vérifie dans Google Cloud Console → Identifiants → ton client OAuth que les deux URIs sont **exactement** : `https://ci-kiaba.com/auth/google/login/callback/` et `http://localhost:8000/auth/google/login/callback/` (avec le slash final). |
| **Bouton Google ne réagit pas / erreur 500** | Vérifie que `GOOGLE_OAUTH_CLIENT_ID` et `GOOGLE_OAUTH_CLIENT_SECRET` sont bien dans `.env` (local) ou dans Vercel (production), et que tu as bien fait `python manage.py migrate`. |
| **« Couldn't import Django »** | Tu n’as pas activé le venv : `source venv/bin/activate` (ou `source .venv/bin/activate`) puis réessaie `python manage.py migrate`. |

Une fois ces étapes faites, connexion et inscription fonctionnent **soit avec Google**, **soit avec email / mot de passe** sur le même site.
