"""
Template tags pour Google AdSense
"""
from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('seo/adsense_ad.html', takes_context=True)
def adsense_ad(context, ad_slot_id=None, ad_format='auto', ad_style='display:block', class_name='adsense-container'):
    """
    Affiche une unité publicitaire AdSense
    
    Usage:
    {% load adsense_tags %}
    {% adsense_ad ad_slot_id="1234567890" %}
    
    Args:
        ad_slot_id: ID de l'unité publicitaire (optionnel, si non fourni, utilise le publisher ID)
        ad_format: Format de l'annonce ('auto', 'rectangle', 'horizontal', 'vertical')
        ad_style: Style CSS inline
        class_name: Classe CSS pour le conteneur
    """
    adsense_enabled = context.get('ADSENSE_ENABLED', False)
    adsense_publisher_id = context.get('ADSENSE_PUBLISHER_ID', None)
    
    # Si AdSense n'est pas activé ou pas de publisher ID, ne rien afficher
    if not adsense_enabled or not adsense_publisher_id:
        return {
            'adsense_enabled': False,
        }
    
    # Si pas d'ad_slot_id, utiliser le publisher ID directement
    if not ad_slot_id:
        ad_slot_id = adsense_publisher_id
    
    return {
        'adsense_enabled': True,
        'adsense_publisher_id': adsense_publisher_id,
        'ad_slot_id': ad_slot_id,
        'ad_format': ad_format,
        'ad_style': ad_style,
        'class_name': class_name,
    }

