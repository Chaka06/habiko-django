from django import template
from django.templatetags.static import static

register = template.Library()


PLACEHOLDER_IMAGES = [
    "page-liste-annonce.PNG",
    "page-detail-annonce.PNG",
    "responsive-mobile-page-liste-annonce.PNG",
    "responsive-mobile-page-detail-annonce.PNG",
]


@register.simple_tag
def ad_placeholder_image(ad):
    """
    Retourne une image de remplacement différente selon l'annonce.
    On utilise l'id de l'annonce pour répartir les images de façon stable.
    """
    if not ad or not getattr(ad, "id", None):
        return static("page-liste-annonce.PNG")
    index = ad.id % len(PLACEHOLDER_IMAGES)
    filename = PLACEHOLDER_IMAGES[index]
    return static(filename)

