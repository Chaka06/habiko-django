"""
Template tags pour le SEO
"""
from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag('seo/breadcrumbs.html', takes_context=True)
def breadcrumbs(context, items=None):
    """
    Affiche les breadcrumbs avec Schema.org
    
    Usage:
    {% load seo_tags %}
    {% breadcrumbs %}
    ou
    {% breadcrumbs items=my_items %}
    """
    if items is None:
        items = context.get('breadcrumbs', [])
    
    # Construire l'URL complète pour chaque item
    breadcrumb_list = []
    for i, item in enumerate(items, start=1):
        if isinstance(item, dict):
            name = item.get('name', '')
            url = item.get('url', '')
        else:
            name = str(item)
            url = ''
        
        # Si l'URL est relative, la rendre absolue
        if url and not url.startswith('http'):
            url = f"https://ci-kiaba.com{url}"
        
        breadcrumb_list.append({
            'position': i,
            'name': name,
            'url': url or f"https://ci-kiaba.com",
        })
    
    return {
        'breadcrumbs': breadcrumb_list,
    }


@register.simple_tag
def breadcrumb_json_ld(items):
    """
    Génère le JSON-LD pour BreadcrumbList
    
    Usage:
    {% breadcrumb_json_ld items=breadcrumb_items %}
    """
    import json
    
    item_list = []
    for i, item in enumerate(items, start=1):
        if isinstance(item, dict):
            name = item.get('name', '')
            url = item.get('url', '')
        else:
            name = str(item)
            url = ''
        
        if url and not url.startswith('http'):
            url = f"https://ci-kiaba.com{url}"
        
        item_list.append({
            "@type": "ListItem",
            "position": i,
            "name": name,
            "item": url or "https://ci-kiaba.com"
        })
    
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": item_list
    }
    
    return json.dumps(schema, ensure_ascii=False)

