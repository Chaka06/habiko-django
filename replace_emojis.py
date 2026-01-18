"""
Script pour remplacer automatiquement les emojis par des icônes Boxicons
dans tous les templates d'emails HABIKO
"""

import os
import re

# Mapping emojis → icônes Boxicons
EMOJI_TO_ICON = {
    '🎉': '<i class="bx bx-party"></i>',
    '🔐': '<i class="bx bx-lock-alt"></i>',
    '✨': '<i class="bx bx-star"></i>',
    '📝': '<i class="bx bx-edit"></i>',
    '🏠': '<i class="bx bx-home"></i>',
    '👤': '<i class="bx bx-user"></i>',
    '📊': '<i class="bx bx-bar-chart-alt-2"></i>',
    '⭐': '<i class="bx bxs-star"></i>',
    '🔔': '<i class="bx bx-bell"></i>',
    '⚠️': '<i class="bx bx-error"></i>',
    '📧': '<i class="bx bx-envelope"></i>',
    '✅': '<i class="bx bx-check-circle"></i>',
    '❌': '<i class="bx bx-x-circle"></i>',
    '💡': '<i class="bx bx-bulb"></i>',
    '📌': '<i class="bx bx-pin"></i>',
    '🏷️': '<i class="bx bx-purchase-tag"></i>',
    '📍': '<i class="bx bx-map"></i>',
    '📅': '<i class="bx bx-calendar"></i>',
    '⏰': '<i class="bx bx-time"></i>',
    '🕐': '<i class="bx bx-time-five"></i>',
    '👁️': '<i class="bx bx-show"></i>',
    '🔥': '<i class="bx bxs-hot"></i>',
    '📸': '<i class="bx bx-camera"></i>',
    '📞': '<i class="bx bx-phone"></i>',
    '🔄': '<i class="bx bx-refresh"></i>',
    '🔑': '<i class="bx bx-key"></i>',
    '🚫': '<i class="bx bx-block"></i>',
    '🔒': '<i class="bx bx-lock"></i>',
    '📢': '<i class="bx bx-megaphone"></i>',
    '🚨': '<i class="bx bx-error-circle"></i>',
    '💬': '<i class="bx bx-message-detail"></i>',
    '📖': '<i class="bx bx-book-open"></i>',
    '✓': '<i class="bx bx-check"></i>',
}

def replace_emojis_in_file(file_path):
    """Remplace les emojis par des icônes dans un fichier"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replacements = 0
        
        # Remplacer chaque emoji
        for emoji, icon in EMOJI_TO_ICON.items():
            if emoji in content:
                count = content.count(emoji)
                content = content.replace(emoji, icon)
                replacements += count
                print(f"  - {emoji} → {icon} ({count}x)")
        
        # Sauvegarder si modifications
        if replacements > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ {file_path}: {replacements} emojis remplacés\n")
            return replacements
        else:
            print(f"⏭️  {file_path}: Aucun emoji trouvé\n")
            return 0
            
    except Exception as e:
        print(f"❌ Erreur avec {file_path}: {e}\n")
        return 0

def main():
    """Point d'entrée principal"""
    print("=" * 70)
    print("REMPLACEMENT EMOJIS → BOXICONS DANS LES TEMPLATES D'EMAILS")
    print("=" * 70)
    print()
    
    # Chemin vers les templates
    templates_dir = '/Users/mac.chaka/Desktop/habiko-django-main/templates/account/email'
    
    if not os.path.exists(templates_dir):
        print(f"❌ Dossier introuvable: {templates_dir}")
        return
    
    # Lister tous les fichiers HTML
    html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
    
    print(f"📁 Dossier: {templates_dir}")
    print(f"📄 Fichiers trouvés: {len(html_files)}")
    print()
    
    total_replacements = 0
    
    # Traiter chaque fichier
    for filename in sorted(html_files):
        file_path = os.path.join(templates_dir, filename)
        print(f"📝 Traitement: {filename}")
        replacements = replace_emojis_in_file(file_path)
        total_replacements += replacements
    
    print("=" * 70)
    print(f"✨ TERMINÉ: {total_replacements} emojis remplacés au total")
    print("=" * 70)

if __name__ == '__main__':
    main()
