"""
Script pour extraire les vraies annonces depuis ci.jedolo.com
Copie EXACTEMENT les titres, descriptions et numéros de téléphone
"""
import re
import requests
from urllib.parse import urljoin
from django.core.management.base import BaseCommand
import json

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class Command(BaseCommand):
    help = "Extrait les vraies annonces depuis ci.jedolo.com avec leurs numéros exacts"

    def handle(self, *args, **options):
        if BeautifulSoup is None:
            self.stdout.write(
                self.style.ERROR("BeautifulSoup4 n'est pas installé")
            )
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

        base_url = "https://ci.jedolo.com"
        extracted_ads = []

        # Essayer de scraper plusieurs pages
        for page in range(1, 11):
            try:
                if page == 1:
                    url = base_url
                else:
                    url = f"{base_url}/?page={page}"

                self.stdout.write(f"Scraping {url}...")
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                # Chercher les liens vers les annonces
                ad_links = soup.find_all("a", href=re.compile(r"/annonce/|/ad/|/detail/|/u/"))
                
                for link in ad_links[:30]:  # Limiter à 30 par page
                    ad_url = urljoin(base_url, link.get("href", ""))
                    if ad_url not in [ad.get("url") for ad in extracted_ads]:
                        ad_data = self.extract_ad_details(ad_url, headers)
                        if ad_data:
                            extracted_ads.append(ad_data)
                            self.stdout.write(f"  → Extrait: {ad_data.get('title', 'N/A')[:50]}...")

                if not ad_links:
                    break

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Erreur page {page}: {str(e)}")
                )
                break

        # Afficher les résultats
        self.stdout.write(f"\n{len(extracted_ads)} annonces extraites")
        
        # Sauvegarder dans un fichier JSON
        output_file = "extracted_jedolo_ads.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(extracted_ads, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(
            self.style.SUCCESS(f"\nDonnées sauvegardées dans {output_file}")
        )
        self.stdout.write("Copiez le contenu dans jedolo_ads_data.py")

    def extract_ad_details(self, url, headers):
        """Extrait les détails d'une annonce"""
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Extraire le titre
            title_elem = soup.find("h1") or soup.find("title")
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Extraire la description
            desc_elem = soup.find("div", class_=re.compile(r"description|content|text|body"))
            if not desc_elem:
                desc_elem = soup.find("p")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Extraire le numéro de téléphone
            phone = None
            # Chercher les numéros dans le texte
            phone_patterns = [
                r"\+225\d{10}",
                r"0[1-9]\d{8}",
                r"225\d{10}",
            ]
            
            page_text = soup.get_text()
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    phone = matches[0]
                    # Convertir en format E.164 si nécessaire
                    if phone.startswith("0"):
                        phone = "+225" + phone[1:]
                    elif phone.startswith("225"):
                        phone = "+" + phone
                    break

            # Déterminer la catégorie
            category = self.determine_category(title, description)
            subcategories = self.determine_subcategories(title, description)

            if title and description:
                return {
                    "url": url,
                    "title": title,
                    "description": description,
                    "phone": phone,
                    "category": category,
                    "subcategories": subcategories,
                }

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Erreur extraction {url}: {str(e)}")
            )

        return None

    def determine_category(self, title, description):
        """Détermine la catégorie"""
        text = (title + " " + description).lower()
        if any(word in text for word in ["massage", "relaxant", "sportif", "chinois", "ivoirien"]):
            return "massages_services"
        elif any(word in text for word in ["sextoy", "jouet", "lubrifiant", "aphrodisiaque"]):
            return "produits_adultes"
        else:
            return "rencontres_escort"

    def determine_subcategories(self, title, description):
        """Détermine les sous-catégories"""
        text = (title + " " + description).lower()
        subcats = []
        
        mapping = {
            "massage sensuel": "Massage sensuel ou érotique",
            "massage ivoirien": "Massage Ivoirien",
            "massage relaxant": "Massage Relaxant",
            "massage sportif": "Massage sportif",
            "massage chinois": "Massage chinois",
            "massage intégral": "Massage Intégral",
            "cherche homme": "Cherche Homme",
            "cherche femme": "Cherche Femme",
            "escort": "Escort Girls",
        }
        
        for keyword, subcat in mapping.items():
            if keyword in text and subcat not in subcats:
                subcats.append(subcat)
                if len(subcats) >= 3:
                    break
        
        return subcats if subcats else ["Escort Girls"]


