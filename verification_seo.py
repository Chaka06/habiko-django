#!/usr/bin/env python3
"""
Script de vérification SEO - Vérifie que tous les templates sont corrects
"""

import os
import re
from pathlib import Path

# Chemins des templates
TEMPLATES_DIR = Path("templates")

# Fichiers modifiés pour le SEO
FILES_TO_CHECK = [
    "templates/core/age_gate.html",
    "templates/ads/detail.html",
    "templates/ads/list.html",
    "templates/core/post.html",
    "templates/core/edit_ad.html",
    "templates/core/dashboard.html",
    "templates/account/login.html",
    "templates/account/signup.html",
    "templates/legal/tos.html",
    "templates/legal/privacy.html",
    "templates/legal/content_policy.html",
]

def check_block_balance(content):
    """Vérifie que les blocs Django sont équilibrés"""
    block_open = len(re.findall(r'{%\s*block\s+', content))
    block_close = len(re.findall(r'{%\s*endblock\s*%}', content))
    return block_open == block_close, block_open, block_close

def check_meta_tags(content, filename):
    """Vérifie la présence des meta tags SEO"""
    issues = []
    
    # Vérifier que les pages privées ont noindex
    private_pages = ['age_gate', 'dashboard', 'login', 'signup']
    is_private = any(page in filename for page in private_pages)
    
    if is_private:
        if 'noindex' not in content or 'nofollow' not in content:
            issues.append(f"⚠️  Page privée sans noindex/nofollow: {filename}")
    
    # Vérifier que les pages publiques ont des meta tags
    if not is_private and 'age_gate' not in filename:
        if 'block title' not in content:
            issues.append(f"⚠️  Pas de block title: {filename}")
        if 'block description' not in content:
            issues.append(f"⚠️  Pas de block description: {filename}")
    
    return issues

def check_seo_keywords(content, filename):
    """Vérifie la présence des mots-clés SEO"""
    keywords = ['kiaba', 'bizi', 'jedolo', 'locanto', 'côte d\'ivoire']
    found_keywords = [kw for kw in keywords if kw.lower() in content.lower()]
    
    # Les pages privées n'ont pas besoin de mots-clés
    private_pages = ['age_gate', 'dashboard', 'login', 'signup']
    is_private = any(page in filename for page in private_pages)
    
    if not is_private and len(found_keywords) < 2:
        return [f"⚠️  Peu de mots-clés SEO trouvés dans {filename}"]
    
    return []

def main():
    """Fonction principale de vérification"""
    print("🔍 Vérification SEO des templates...\n")
    
    all_issues = []
    all_errors = []
    
    for filepath in FILES_TO_CHECK:
        if not os.path.exists(filepath):
            all_errors.append(f"❌ Fichier introuvable: {filepath}")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(filepath)
        
        # Vérifier l'équilibre des blocs
        balanced, open_count, close_count = check_block_balance(content)
        if not balanced:
            all_errors.append(f"❌ Blocs déséquilibrés dans {filename}: {open_count} ouverts, {close_count} fermés")
        
        # Vérifier les meta tags
        meta_issues = check_meta_tags(content, filename)
        all_issues.extend(meta_issues)
        
        # Vérifier les mots-clés SEO
        keyword_issues = check_seo_keywords(content, filename)
        all_issues.extend(keyword_issues)
        
        if balanced and not meta_issues and not keyword_issues:
            print(f"✅ {filename}")
    
    print("\n" + "="*60)
    
    if all_errors:
        print("\n❌ ERREURS CRITIQUES:")
        for error in all_errors:
            print(f"  {error}")
    
    if all_issues:
        print("\n⚠️  AVERTISSEMENTS:")
        for issue in all_issues:
            print(f"  {issue}")
    
    if not all_errors and not all_issues:
        print("\n✅ TOUS LES FICHIERS SONT CORRECTS !")
        print("\n✅ Vérifications réussies:")
        print("  ✅ Tous les blocs sont équilibrés")
        print("  ✅ Tous les meta tags sont présents")
        print("  ✅ Les mots-clés SEO sont présents")
        print("  ✅ Les pages privées ont noindex/nofollow")
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())

