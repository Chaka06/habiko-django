# 🧹 Nettoyage de l'historique Git - Suppression des secrets

## Problème
GitHub/GitGuardian détecte encore les secrets dans l'historique Git, même si le fichier `render.yaml` actuel est propre. Les secrets sont toujours présents dans les anciens commits.

## Solution : Nettoyer l'historique Git

### Option 1 : Utiliser git-filter-repo (Recommandé)

```bash
# Installer git-filter-repo
pip install git-filter-repo

# Nettoyer l'historique
git filter-repo --path render.yaml --replace-text <(echo "GIC0OwgP0ACv90JSg1EH19Hre1Ndg1ir==>REMOVED_SECRET") --force
git filter-repo --path render.yaml --replace-text <(echo "mail55.lwspanel.com==>REMOVED_HOST") --force

# Forcer le push (⚠️ réécrit l'historique)
git push origin --force --all
```

### Option 2 : Utiliser BFG Repo-Cleaner

```bash
# Télécharger BFG depuis https://rtyley.github.io/bfg-repo-cleaner/
# Créer un fichier secrets.txt avec les patterns à remplacer:
echo "GIC0OwgP0ACv90JSg1EH19Hre1Ndg1ir==>REMOVED_SECRET" > secrets.txt
echo "mail55.lwspanel.com==>REMOVED_HOST" >> secrets.txt

# Nettoyer
java -jar bfg.jar --replace-text secrets.txt

# Nettoyer les références
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Forcer le push
git push origin --force --all
```

### Option 3 : Utiliser le script fourni

```bash
# Exécuter le script de nettoyage
./clean_secrets.sh

# Puis forcer le push
git push origin --force --all
```

## ⚠️ AVANT DE CONTINUER

1. **Sauvegarder votre dépôt** : Faire une copie complète avant de modifier l'historique
2. **Vérifier les collaborateurs** : S'assurer que personne d'autre ne travaille sur ce dépôt
3. **Changer tous les secrets** : Les secrets exposés doivent être changés immédiatement :
   - Mot de passe PostgreSQL : `GIC0OwgP0ACv90JSg1EH19Hre1Ndg1ir`
   - Serveur SMTP : `mail55.lwspanel.com`
   - Tous les autres mots de passe/clés API

## 📋 Checklist après nettoyage

- [ ] Historique Git nettoyé
- [ ] `git push --force` effectué
- [ ] Tous les secrets changés dans Render
- [ ] Variables d'environnement configurées dans Render dashboard
- [ ] GitHub/GitGuardian ne détecte plus de secrets
- [ ] Application fonctionne correctement après les changements

## 🔄 Alternative : Créer un nouveau dépôt (si le nettoyage est trop complexe)

Si le nettoyage de l'historique est trop risqué, vous pouvez :

1. Créer un nouveau dépôt GitHub
2. Copier uniquement les fichiers actuels (sans l'historique)
3. Changer tous les secrets
4. Mettre à jour Render pour pointer vers le nouveau dépôt

```bash
# Créer un nouveau dépôt sans historique
git checkout --orphan new-master
git add .
git commit -m "Initial commit - sans secrets"
git remote set-url origin <nouveau-repo-url>
git push -u origin new-master
```
