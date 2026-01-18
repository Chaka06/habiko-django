"""
Script pour télécharger les images depuis ci.jedolo.com
"""
import os
import re
import requests
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class Command(BaseCommand):
    help = "Télécharge les images depuis ci.jedolo.com et les stocke dans static/jedolo_images/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-images",
            type=int,
            default=100,
            help="Nombre maximum d'images à télécharger (défaut: 100)",
        )

    def handle(self, *args, **options):
        if BeautifulSoup is None:
            self.stdout.write(
                self.style.ERROR("BeautifulSoup4 n'est pas installé. Installez-le avec: pip install beautifulsoup4")
            )
            return

        max_images = options["max_images"]
        
        # Créer le dossier pour stocker les images
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        # Sauvegarder dans static/ pour que les images soient dans le repo
        images_dir = base_dir / "static" / "jedolo_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write(f"Téléchargement des images dans: {images_dir}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        downloaded = 0
        base_url = "https://ci.jedolo.com"
        
        # URLs à scraper pour trouver des images
        urls_to_scrape = [
            base_url,
            f"{base_url}/u/rencontres-en-ligne-jedolo-cote-d-ivoire",
            f"{base_url}/annonces",
        ]
        
        image_urls = set()
        
        # Scraper les pages pour trouver des images
        for url in urls_to_scrape:
            try:
                self.stdout.write(f"Scraping {url}...")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Trouver toutes les images
                img_tags = soup.find_all("img")
                
                for img in img_tags:
                    # Essayer plusieurs attributs pour trouver l'URL de l'image
                    img_url = (
                        img.get("src") or 
                        img.get("data-src") or 
                        img.get("data-lazy-src") or
                        img.get("data-original") or
                        img.get("data-url")
                    )
                    if img_url:
                        # Convertir en URL absolue
                        img_url = urljoin(url, img_url)
                        
                        # Filtrer les images pertinentes
                        if self.is_valid_image_url(img_url):
                            image_urls.add(img_url)
                
                # Chercher aussi dans les balises <a> avec des liens vers des images
                link_tags = soup.find_all("a", href=re.compile(r"\.(jpg|jpeg|png|webp|gif)", re.I))
                for link in link_tags:
                    href = link.get("href")
                    if href:
                        img_url = urljoin(url, href)
                        if self.is_valid_image_url(img_url):
                            image_urls.add(img_url)
                            
                self.stdout.write(f"  → {len(image_urls)} URLs d'images trouvées")
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Erreur lors du scraping de {url}: {str(e)}")
                )
        
        # Télécharger les images
        self.stdout.write(f"\nTéléchargement de {min(len(image_urls), max_images)} images...")
        
        for idx, img_url in enumerate(list(image_urls)[:max_images]):
            try:
                response = requests.get(img_url, headers=headers, timeout=10, stream=True)
                response.raise_for_status()
                
                # Vérifier que c'est bien une image
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    continue
                
                # Déterminer l'extension
                parsed = urlparse(img_url)
                ext = os.path.splitext(parsed.path)[1]
                if not ext or ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    ext = ".jpg"
                
                # Nom du fichier
                filename = f"jedolo_{idx+1}{ext}"
                filepath = images_dir / filename
                
                # Télécharger et sauvegarder
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                downloaded += 1
                
                if downloaded % 10 == 0:
                    self.stdout.write(f"  → {downloaded} images téléchargées...")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Erreur lors du téléchargement de {img_url}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"\n{downloaded} images téléchargées dans {images_dir}")
        )

    def is_valid_image_url(self, url):
        """Vérifie si l'URL d'image est valide"""
        url_lower = url.lower()
        
        # Exclure les logos, icônes, etc.
        exclude_patterns = [
            "logo", "icon", "avatar", "default", "placeholder",
            "banner", "header", "footer", "social", "facebook",
            "twitter", "instagram", "youtube", "pinterest",
        ]
        
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        # Vérifier l'extension
        valid_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        if not any(url_lower.endswith(ext) for ext in valid_extensions):
            return False
        
        return True

