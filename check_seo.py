#!/usr/bin/env python
"""
Script de vérification SEO pour KIABA
Vérifie que tous les éléments critiques pour l'indexation sont en place
"""
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kiaba.settings')

import django
django.setup()

from django.urls import reverse
from django.test import Client
from django.contrib.sitemaps import get_sitemap_urls

def check_robots_txt():
    """Vérifier que robots.txt est accessible et correct"""
    print("🔍 Vérification de robots.txt...")
    client = Client()
    response = client.get('/robots.txt')
    
    if response.status_code == 200:
        content = response.content.decode()
        if 'Sitemap:' in content and 'ci-habiko.com' in content:
            print("✅ robots.txt : OK")
            return True
        else:
            print("❌ robots.txt : Sitemap manquant")
            return False
    else:
        print(f"❌ robots.txt : Erreur {response.status_code}")
        return False

def check_sitemap():
    """Vérifier que le sitemap est accessible"""
    print("🔍 Vérification du sitemap...")
    client = Client()
    response = client.get('/sitemap.xml')
    
    if response.status_code == 200:
        content = response.content.decode()
        if '<?xml' in content and '<urlset' in content:
            print("✅ sitemap.xml : OK")
            # Compter les URLs
            url_count = content.count('<url>')
            print(f"   📊 {url_count} URLs trouvées dans le sitemap")
            return True
        else:
            print("❌ sitemap.xml : Format invalide")
            return False
    else:
        print(f"❌ sitemap.xml : Erreur {response.status_code}")
        return False

def check_homepage():
    """Vérifier que la page d'accueil est accessible"""
    print("🔍 Vérification de la page d'accueil...")
    client = Client()
    # Simuler un robot de recherche
    response = client.get('/', HTTP_USER_AGENT='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)')
    
    if response.status_code == 200:
        content = response.content.decode()
        # Vérifier les meta tags SEO
        checks = {
            'meta name="description"': 'description' in content.lower(),
            'meta name="keywords"': 'keywords' in content.lower(),
            'meta name="robots"': 'robots' in content.lower() and 'index' in content.lower(),
            'canonical': 'canonical' in content.lower(),
            'og:title': 'og:title' in content.lower(),
            'JSON-LD': 'application/ld+json' in content,
        }
        
        all_ok = all(checks.values())
        if all_ok:
            print("✅ Page d'accueil : OK")
            print("   ✅ Tous les meta tags SEO présents")
        else:
            print("⚠️  Page d'accueil : Certains éléments manquent")
            for check, result in checks.items():
                status = "✅" if result else "❌"
                print(f"   {status} {check}")
        return all_ok
    else:
        print(f"❌ Page d'accueil : Erreur {response.status_code}")
        return False

def check_legal_pages():
    """Vérifier que les pages légales sont accessibles"""
    print("🔍 Vérification des pages légales...")
    client = Client()
    pages = [
        ('/legal/tos', 'CGU'),
        ('/legal/privacy', 'Confidentialité'),
        ('/legal/content-policy', 'Politique de contenu'),
    ]
    
    all_ok = True
    for url, name in pages:
        response = client.get(url, HTTP_USER_AGENT='Mozilla/5.0 (compatible; Googlebot/2.1)')
        if response.status_code == 200:
            print(f"✅ {name} : OK")
        else:
            print(f"❌ {name} : Erreur {response.status_code}")
            all_ok = False
    
    return all_ok

def check_age_gate_bypass():
    """Vérifier que les robots peuvent contourner l'age gate"""
    print("🔍 Vérification du bypass age gate pour les robots...")
    client = Client()
    
    # Test sans user-agent (doit rediriger vers age-gate)
    response = client.get('/')
    if response.status_code == 302 and '/age-gate/' in response.url:
        print("✅ Age gate : Redirection normale pour utilisateurs")
    else:
        print("⚠️  Age gate : Comportement inattendu")
    
    # Test avec user-agent Googlebot (doit accéder directement)
    response = client.get('/', HTTP_USER_AGENT='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)')
    if response.status_code == 200:
        print("✅ Age gate : Bypass pour robots OK")
        return True
    else:
        print(f"❌ Age gate : Erreur {response.status_code} pour robots")
        return False

def main():
    print("=" * 60)
    print("🔍 VÉRIFICATION SEO KIABA")
    print("=" * 60)
    print()
    
    results = []
    results.append(("robots.txt", check_robots_txt()))
    results.append(("sitemap.xml", check_sitemap()))
    results.append(("Page d'accueil", check_homepage()))
    results.append(("Pages légales", check_legal_pages()))
    results.append(("Age gate bypass", check_age_gate_bypass()))
    
    print()
    print("=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print()
    print(f"Score : {passed}/{total} ({passed*100//total}%)")
    
    if passed == total:
        print()
        print("🎉 Tous les tests sont passés !")
        print("✅ Le site est prêt pour l'indexation Google")
        print()
        print("📋 Prochaines étapes :")
        print("1. Aller sur https://search.google.com/search-console")
        print("2. Ajouter la propriété : https://ci-habiko.com")
        print("3. Soumettre le sitemap : https://ci-habiko.com/sitemap.xml")
        print("4. Demander l'indexation de la page d'accueil")
    else:
        print()
        print("⚠️  Certains tests ont échoué")
        print("Vérifiez les erreurs ci-dessus et corrigez-les")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

