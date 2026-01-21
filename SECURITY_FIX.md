# 🔒 CORRECTION DE SÉCURITÉ - Secrets exposés

## Problème détecté
GitGuardian a détecté des identifiants SMTP et autres secrets exposés dans le dépôt GitHub.

## Actions effectuées

### 1. ✅ Fichier `render.yaml`
- **Retiré** : Tous les mots de passe, clés API et identifiants
- **Remplacé par** : Des commentaires indiquant d'utiliser les variables d'environnement dans le dashboard Render
- **Secrets exposés qui ont été retirés** :
  - `POSTGRES_PASSWORD`: `GIC0OwgP0ACv90JSg1EH19Hre1Ndg1ir`
  - `EMAIL_HOST_PASSWORD`: (mot de passe SMTP)
  - `CINETPAY_API_KEY`: `1317052651681a6fdef33a80.27918103`
  - `CINETPAY_SITE_KEY`: `9694017766946fdd7c66b09.59234458`

### 2. ✅ Fichier `create_initial_superuser.py`
- **Modifié** : Utilise maintenant `INITIAL_SUPERUSER_PASSWORD` depuis les variables d'environnement
- **Recommandation** : Changer le mot de passe du superutilisateur `kaliadmin2` immédiatement

### 3. ✅ Fichier `.env`
- **Vérifié** : Le fichier `.env` est dans `.gitignore` et ne devrait plus être commité
- **Action requise** : Si le fichier `.env` a été commité dans le passé, il reste dans l'historique Git

## ⚠️ ACTIONS URGENTES REQUISES

### 1. Changer tous les mots de passe/clés exposés

#### Base de données PostgreSQL
- **Changer le mot de passe** de la base de données sur Render
- Mettre à jour la variable d'environnement `POSTGRES_PASSWORD` dans le dashboard Render

#### Email SMTP
- **Changer le mot de passe SMTP** sur votre serveur de messagerie (LWS Panel)
- Mettre à jour la variable d'environnement `EMAIL_HOST_PASSWORD` dans le dashboard Render

#### CinetPay
- **Régénérer les clés API** sur le dashboard CinetPay
- Mettre à jour les variables d'environnement dans Render :
  - `CINETPAY_API_KEY`
  - `CINETPAY_SITE_KEY`

#### Superutilisateur Django
- **Changer le mot de passe** du superutilisateur `kaliadmin2` dans Django Admin
- Ou définir `INITIAL_SUPERUSER_PASSWORD` dans les variables d'environnement Render

### 2. Configurer les variables d'environnement dans Render

1. Aller sur https://dashboard.render.com
2. Sélectionner votre service web
3. Aller dans "Environment"
4. Ajouter toutes les variables d'environnement nécessaires (voir `render.yaml` pour la liste)

### 3. Nettoyer l'historique Git (optionnel mais recommandé)

Si le fichier `.env` a été commité dans le passé, il reste dans l'historique Git. Pour le retirer complètement :

```bash
# Option 1: Utiliser git-filter-repo (recommandé)
pip install git-filter-repo
git filter-repo --path .env --invert-paths

# Option 2: Utiliser BFG Repo-Cleaner
# Télécharger depuis https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**⚠️ IMPORTANT** : Après avoir nettoyé l'historique, vous devrez faire un `git push --force` sur toutes les branches. Cela réécrira l'historique Git.

## ✅ Vérifications

- [ ] Tous les mots de passe ont été changés
- [ ] Toutes les clés API ont été régénérées
- [ ] Les variables d'environnement sont configurées dans Render
- [ ] Le fichier `.env` est dans `.gitignore`
- [ ] Aucun secret n'est présent dans les fichiers commités

## 📝 Notes

- Le fichier `render.yaml` contient maintenant uniquement des commentaires et des placeholders
- Tous les secrets doivent être configurés via les variables d'environnement dans le dashboard Render
- Ne jamais commiter de fichiers contenant des secrets (`.env`, `*.key`, etc.)
