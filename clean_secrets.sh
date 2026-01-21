#!/bin/bash
# Script pour nettoyer les secrets de l'historique Git
# ATTENTION: Ce script réécrit l'historique Git. Utilisez-le avec précaution.

set -e

echo "🔒 Nettoyage des secrets de l'historique Git..."
echo "⚠️  Ce script va réécrire l'historique Git."
echo ""

# Vérifier si git-filter-repo est installé
if command -v git-filter-repo &> /dev/null; then
    echo "✅ git-filter-repo trouvé, utilisation de cette méthode..."
    git filter-repo --path render.yaml --invert-paths --force
    git filter-repo --path render.yaml --use-base-name --force
    # Réécrire render.yaml sans les secrets
    git filter-repo --path render.yaml --replace-text <(echo "GIC0OwgP0ACv90JSg1EH19Hre1Ndg1ir==>REMOVED_SECRET") --force
    echo "✅ Nettoyage terminé avec git-filter-repo"
elif command -v bfg &> /dev/null || [ -f "bfg.jar" ]; then
    echo "✅ BFG Repo-Cleaner trouvé, utilisation de cette méthode..."
    if [ -f "bfg.jar" ]; then
        java -jar bfg.jar --replace-text secrets.txt
    else
        bfg --replace-text secrets.txt
    fi
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
    echo "✅ Nettoyage terminé avec BFG"
else
    echo "⚠️  git-filter-repo ou BFG non trouvé."
    echo "📝 Installation recommandée:"
    echo "   pip install git-filter-repo"
    echo "   ou"
    echo "   Télécharger BFG: https://rtyley.github.io/bfg-repo-cleaner/"
    echo ""
    echo "🔄 Utilisation de git filter-branch (méthode alternative)..."
    FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --force --index-filter \
        'git checkout HEAD -- render.yaml && \
         sed -i "s/GIC0OwgP0ACv90JSg1EH19Hre1Ndg1ir/REMOVED_SECRET/g" render.yaml && \
         sed -i "s/mail55\.lwspanel\.com/REMOVED_HOST/g" render.yaml && \
         git add render.yaml' \
        --prune-empty --tag-name-filter cat -- --all
    
    # Nettoyer les références
    git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
    
    echo "✅ Nettoyage terminé avec git filter-branch"
fi

echo ""
echo "✅ Nettoyage terminé!"
echo "⚠️  IMPORTANT: Vous devez maintenant faire un 'git push --force' pour mettre à jour le dépôt distant."
echo "⚠️  ATTENTION: Cela réécrira l'historique sur GitHub. Assurez-vous que personne d'autre ne travaille sur ce dépôt."
