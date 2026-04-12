"""
Commande pour importer des annonces depuis ci.jedolo.com
Usage :
    python manage.py import_jedolo --pages 15 --delay 2
    python manage.py import_jedolo --pages 15 --delay 2 --dry-run
"""
import time
import re
import logging
from io import BytesIO
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image

from ads.models import Ad, AdMedia, City

logger = logging.getLogger(__name__)
User = get_user_model()

BASE_URL = "https://ci.jedolo.com"
CDN_URL  = "https://cdn.jedolo.com/ci/"

# Liste des pages à scraper (dernières annonces escortes)
LIST_URL = "https://ci.jedolo.com/dernieres-annonces-rencontres.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://ci.jedolo.com/",
}

# Mapping ville jedolo → slug KIABA
# La plupart sont devinables depuis l'URL (rencontre-abidjan → abidjan)
# On crée automatiquement les villes manquantes.
CITY_NAME_MAP = {
    "abidjan": "Abidjan",
    "bouake": "Bouaké",
    "daloa": "Daloa",
    "yamoussoukro": "Yamoussoukro",
    "korhogo": "Korhogo",
    "san-pedro": "San-Pédro",
    "grand-bassam": "Grand-Bassam",
    "bingerville": "Bingerville",
    "divo": "Divo",
    "man": "Man",
    "gagnoa": "Gagnoa",
    "soubre": "Soubré",
    "abengourou": "Abengourou",
    "bondoukou": "Bondoukou",
    "odienne": "Odienné",
    "touba": "Touba",
    "guiglo": "Guiglo",
    "sassandra": "Sassandra",
    "jacqueville": "Jacqueville",
    "anyama": "Anyama",
}


def _get_or_create_city(slug_part: str) -> City:
    """Retourne ou crée la ville KIABA depuis le slug jedolo (ex: 'abidjan')."""
    slug = slugify(slug_part)
    try:
        return City.objects.get(slug=slug)
    except City.DoesNotExist:
        name = CITY_NAME_MAP.get(slug_part, slug_part.replace("-", " ").title())
        city = City(name=name, slug=slug)
        city.save()
        return city


def _get_system_user() -> User:
    """Retourne le premier superuser ou le premier user disponible."""
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    if not user:
        raise RuntimeError("Aucun utilisateur trouvé en base — crée d'abord un superuser.")
    return user


def _detect_category(title: str, description: str = "") -> str:
    """
    Détecte la catégorie KIABA depuis le titre et la description de l'annonce.
    On n'utilise PAS le texte complet de la page (inclut la nav jedolo
    qui contient 'transgenre' sur chaque page).
    """
    t = (title + " " + description[:500]).lower()
    if any(w in t for w in ["transgenre", "travesti", "trans ", "trav "]):
        return Ad.Category.TRANSGENRE
    if any(w in t for w in [" homme", "escort boy", "bizi boy", " mec ", "jeune homme", "guy"]):
        return Ad.Category.ESCORTE_BOY
    # Défaut : escorte_girl (majorité des annonces jedolo sont féminines)
    return Ad.Category.ESCORTE_GIRL


def _extract_city_slug_from_url(url: str) -> str:
    """Extrait 'abidjan' depuis '//ci.jedolo.com/rencontre-abidjan/...'."""
    m = re.search(r"/rencontre-([^/]+)/", url)
    return m.group(1) if m else "abidjan"


def _extract_jedolo_id(url: str) -> str | None:
    """Extrait l'ID jedolo depuis l'URL (ex: 440762)."""
    m = re.search(r"-(\d+)\.html$", url)
    return m.group(1) if m else None


def _fetch(url: str, session: requests.Session, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            logger.warning("Tentative %d/%d échouée pour %s : %s", attempt + 1, retries, url, e)
            time.sleep(2)
    return None


def _download_image(url: str, session: requests.Session, referer: str = BASE_URL) -> bytes | None:
    headers = {**HEADERS, "Referer": referer}
    try:
        r = session.get(url, headers=headers, timeout=30, stream=True)
        r.raise_for_status()
        # Vérifier que c'est bien une image (pas une page HTML d'erreur)
        ct = r.headers.get("Content-Type", "")
        if "html" in ct:
            logger.warning("URL image retourne du HTML (accès bloqué ?) : %s", url)
            return None
        buf = BytesIO()
        for chunk in r.iter_content(8192):
            buf.write(chunk)
        data = buf.getvalue()
        if len(data) < 1000:  # image trop petite = probablement une erreur
            logger.warning("Image trop petite (%d octets), ignorée : %s", len(data), url)
            return None
        return data
    except Exception as e:
        logger.warning("Impossible de télécharger %s : %s", url, e)
        return None


def _scrape_ad_detail(url: str, session: requests.Session) -> dict | None:
    """Scrape une page d'annonce jedolo et retourne un dict de données."""
    full_url = url if url.startswith("http") else "https:" + url
    soup = _fetch(full_url, session)
    if not soup:
        return None

    # ── Titre ──
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    if not title:
        return None
    # Nettoyer : jedolo colle des noms de ville à la fin du H1 (ex: "...baizAbidjanAbidjan")
    # On retire les morceaux répétés de villes ivoiriennes en fin de titre
    title = re.sub(
        r"(Abidjan|Bouaké|Daloa|Yamoussoukro|Korhogo|Bingerville|Bassam|Grand-Bassam|"
        r"Anyama|Divo|Soubré|Man|Gagnoa|San-Pédro|Sassandra|Jacqueville){1,3}\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()
    # Titre générique jedolo → annonce inutile, on skip
    if title.lower().startswith("annonces rencontres") or len(title) < 10:
        return None
    title = title[:140]

    # ── Description ──
    # jedolo met la description dans un div avec id ou classe contenant "description"
    desc_el = (
        soup.find("div", {"id": re.compile(r"description", re.I)})
        or soup.find("div", {"class": re.compile(r"description", re.I)})
        or soup.find("div", {"class": "ad-details"})
        or soup.find("div", {"class": "content"})
    )
    description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""
    # Fallback : tout le texte du main/article
    if len(description) < 30:
        main = soup.find("main") or soup.find("article") or soup.find("body")
        description = main.get_text(separator="\n", strip=True)[:2000] if main else ""
    description = description[:3000]

    # ── Catégorie ── (titre + début de description, pas la page entière)
    category = _detect_category(title, description)

    # ── Ville ──
    city_slug = _extract_city_slug_from_url(full_url)

    # ── Images ──
    image_urls = []
    # Images pleine résolution : cdn.jedolo.com/ci/CODE.jpg (sans "thumbs/tn_")
    for img in soup.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "")
        if "cdn.jedolo.com" in src:
            # Convertir thumbnail en pleine résolution
            full = re.sub(r"thumbs/tn_", "", src)
            if full not in image_urls:
                image_urls.append(full)

    # Galerie via liens <a href="...cdn.jedolo.com...">
    for a in soup.find_all("a", href=re.compile(r"cdn\.jedolo\.com")):
        href = a["href"]
        if href not in image_urls:
            image_urls.append(href)

    image_urls = [u if u.startswith("http") else "https:" + u for u in image_urls[:5]]

    # ── ID jedolo ──
    jedolo_id = _extract_jedolo_id(full_url)

    return {
        "title": title,
        "description": description,
        "category": category,
        "city_slug": city_slug,
        "image_urls": image_urls,
        "jedolo_id": jedolo_id,
        "source_url": full_url,  # stockée en base pour le backfill
    }


def _create_ad(data: dict, user, dry_run: bool = False, session: requests.Session = None) -> bool:
    """Crée l'annonce + médias en base. Retourne True si créée."""
    # Déduplication par jedolo_id
    jedolo_id = data.get("jedolo_id")
    if jedolo_id and Ad.objects.filter(additional_data__jedolo_id=jedolo_id).exists():
        return False

    city = _get_or_create_city(data["city_slug"])

    if dry_run:
        print(f"  [DRY-RUN] {data['title'][:60]} | {data['category']} | {city.name} | {len(data['image_urls'])} photo(s)")
        return True

    ad = Ad(
        user=user,
        title=data["title"][:140],
        description_sanitized=data["description"] or data["title"],
        category=data["category"],
        city=city,
        status=Ad.Status.APPROVED,
        image_processing_done=True,
        subcategories=[],
        additional_data={
            "jedolo_id": jedolo_id,
            "source": "jedolo",
            "source_url": data.get("source_url", ""),
        },
        expires_at=timezone.now() + timezone.timedelta(days=365),
    )
    ad.save()

    # Télécharger et attacher les images
    # On réutilise la session de scraping (cookies inclus) pour le CDN
    dl_session = session or requests.Session()
    source_url = data.get("source_url", BASE_URL)
    photo_count = 0
    if not data["image_urls"]:
        print(f"    ⚠ Aucune URL d'image trouvée pour cette annonce")
    for idx, img_url in enumerate(data["image_urls"]):
        print(f"    → téléchargement image {idx+1}: {img_url[:80]}")
        img_bytes = _download_image(img_url, dl_session, referer=source_url)
        if not img_bytes:
            print(f"    ✗ Échec image {idx+1}")
            continue
        ext = "jpg"
        m = re.search(r"\.(jpg|jpeg|png|webp)(\?.*)?$", img_url, re.I)
        if m:
            ext = m.group(1).lower()
        filename = f"jedolo_{jedolo_id or ad.pk}_{idx}.{ext}"
        media = AdMedia(ad=ad, is_primary=(idx == 0))
        media.image.save(filename, ContentFile(img_bytes), save=False)
        media._watermark_applied = True   # on bypass le filigrane à l'import
        # Générer le thumbnail maintenant (Celery peut ne pas tourner en dev)
        _generate_thumbnail(media, img_bytes)
        media.save()
        photo_count += 1
        print(f"    ✓ Image {idx+1} sauvegardée ({len(img_bytes)//1024}ko)")
        if photo_count >= 3:
            break

    return True


def _generate_thumbnail(media: AdMedia, img_bytes: bytes) -> None:
    """Génère un thumbnail 320×320 sans filigrane et l'attache au média (avant save)."""
    try:
        img = Image.open(BytesIO(img_bytes))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        elif img.mode == "RGBA":
            img = img.convert("RGB")
        img.thumbnail((320, 320), Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=55, optimize=True)
        buf.seek(0)
        base = re.sub(r"\.[^.]+$", "", media.image.name or "image")
        thumb_name = f"{base}_thumb.webp"
        media.thumbnail.save(thumb_name, ContentFile(buf.read()), save=False)
    except Exception as e:
        logger.warning("Thumbnail non généré pour %s : %s", media.image.name, e)


class Command(BaseCommand):
    help = "Importe des annonces depuis ci.jedolo.com (autorisation obtenue)"

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=15, help="Nombre de pages à scraper (défaut: 15, ~20 annonces/page)")
        parser.add_argument("--delay", type=float, default=2.0, help="Délai en secondes entre chaque annonce (défaut: 2)")
        parser.add_argument("--dry-run", action="store_true", help="Affiche ce qui serait importé sans rien écrire en base")
        parser.add_argument("--start-page", type=int, default=1, help="Page de départ (défaut: 1)")
        parser.add_argument("--backfill-images", action="store_true", help="Re-télécharge les images des annonces jedolo qui n'en ont pas encore")

    def handle(self, *args, **options):
        pages = options["pages"]
        delay = options["delay"]
        dry_run = options["dry_run"]
        start_page = options["start_page"]
        backfill = options["backfill_images"]

        user = _get_system_user()
        session = requests.Session()

        if backfill:
            self._backfill_images(session, delay)
            return

        self.stdout.write(f"Utilisateur système : {user.username}")
        self.stdout.write(f"Pages : {start_page} → {start_page + pages - 1} | délai : {delay}s | dry-run : {dry_run}")

        total_created = 0
        total_skipped = 0
        total_errors = 0

        for page_num in range(start_page, start_page + pages):
            url = f"{LIST_URL}?page={page_num}" if page_num > 1 else LIST_URL
            self.stdout.write(f"\n── Page {page_num} : {url}")

            soup = _fetch(url, session)
            if not soup:
                self.stderr.write(f"  Impossible de charger la page {page_num}, on continue.")
                continue

            # Extraire les liens d'annonces
            ad_links = []
            for a in soup.find_all("a", href=re.compile(r"/rencontre-[^/]+/.+-\d+\.html")):
                href = a["href"]
                full = href if href.startswith("http") else "https:" + href
                if full not in ad_links:
                    ad_links.append(full)

            if not ad_links:
                self.stdout.write("  Aucun lien trouvé sur cette page, fin du scraping.")
                break

            self.stdout.write(f"  {len(ad_links)} annonce(s) trouvée(s)")

            for ad_url in ad_links:
                jedolo_id = _extract_jedolo_id(ad_url)
                if jedolo_id and not dry_run:
                    if Ad.objects.filter(additional_data__jedolo_id=jedolo_id).exists():
                        total_skipped += 1
                        continue

                data = _scrape_ad_detail(ad_url, session)
                if not data:
                    total_errors += 1
                    self.stderr.write(f"  ✗ Échec scraping : {ad_url}")
                    continue

                try:
                    created = _create_ad(data, user, dry_run=dry_run, session=session)
                    if created:
                        total_created += 1
                        self.stdout.write(
                            f"  ✓ {'[DRY]' if dry_run else 'Créée'} : {data['title'][:55]} ({data['category']}, {data['city_slug']})"
                        )
                    else:
                        total_skipped += 1
                except Exception as e:
                    total_errors += 1
                    self.stderr.write(f"  ✗ Erreur création : {ad_url} — {e}")

                time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n═══ Terminé ═══\n"
                f"  Créées  : {total_created}\n"
                f"  Ignorées (doublons) : {total_skipped}\n"
                f"  Erreurs : {total_errors}"
            )
        )

    def _backfill_images(self, session: requests.Session, delay: float) -> None:
        """Re-télécharge les images des annonces jedolo qui n'en ont pas encore."""
        from ads.models import AdMedia

        ads_no_img = (
            Ad.objects.filter(additional_data__source="jedolo")
            .exclude(id__in=AdMedia.objects.values("ad_id"))
        )
        total = ads_no_img.count()
        self.stdout.write(f"Backfill images : {total} annonce(s) jedolo sans images trouvée(s)")

        done = 0
        errors = 0
        for ad in ads_no_img:
            source_url = ad.additional_data.get("source_url", "")
            jedolo_id = ad.additional_data.get("jedolo_id", "")
            if not source_url:
                self.stderr.write(f"  ✗ Pas de source_url pour pk={ad.pk} (jedolo_id={jedolo_id}), ignoré")
                errors += 1
                continue

            self.stdout.write(f"  → {ad.title[:60]} ({jedolo_id})")
            data = _scrape_ad_detail(source_url, session)
            if not data or not data["image_urls"]:
                self.stderr.write(f"    ✗ Aucune image trouvée sur {source_url}")
                errors += 1
                time.sleep(delay)
                continue

            photo_count = 0
            for idx, img_url in enumerate(data["image_urls"]):
                img_bytes = _download_image(img_url, session, referer=source_url)
                if not img_bytes:
                    continue
                ext = "jpg"
                m = re.search(r"\.(jpg|jpeg|png|webp)(\?.*)?$", img_url, re.I)
                if m:
                    ext = m.group(1).lower()
                filename = f"jedolo_{jedolo_id or ad.pk}_{idx}.{ext}"
                media = AdMedia(ad=ad, is_primary=(idx == 0))
                media.image.save(filename, ContentFile(img_bytes), save=False)
                media._watermark_applied = True
                _generate_thumbnail(media, img_bytes)
                media.save()
                photo_count += 1
                self.stdout.write(f"    ✓ Image {idx+1} ({len(img_bytes)//1024}ko)")
                if photo_count >= 3:
                    break

            done += 1
            time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n═══ Backfill terminé ═══\n"
                f"  Traitées : {done}\n"
                f"  Erreurs  : {errors}"
            )
        )
