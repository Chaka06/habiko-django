# Configuration Cloudflare pour HABIKO

## 🎯 Pourquoi Cloudflare ?

Cloudflare apporte plusieurs avantages importants à HABIKO :

1. **CDN (Content Delivery Network)** : Accélère le chargement des assets statiques
2. **Protection DDoS** : Protège contre les attaques
3. **SSL/TLS gratuit** : Certificats SSL automatiques
4. **Cache** : Réduit la charge sur Render
5. **Sécurité** : Firewall, protection bot, etc.
6. **Analytics** : Statistiques détaillées

## 📋 Étapes de configuration

### Étape 1 : Créer un compte Cloudflare

1. Aller sur https://dash.cloudflare.com/sign-up
2. Créer un compte gratuit (plan Free suffit pour commencer)
3. Ajouter votre site : `ci-habiko.com`

### Étape 2 : Configurer les DNS dans LWS Panel

**Important** : Il faut d'abord configurer Cloudflare, puis mettre à jour les DNS dans LWS.

1. **Dans Cloudflare** :
   - Cloudflare va te donner 2 serveurs de noms (nameservers)
   - Exemple : `dana.ns.cloudflare.com` et `jim.ns.cloudflare.com`

2. **Dans LWS Panel** :
   - Aller dans la gestion de ton domaine `ci-habiko.com`
   - Modifier les nameservers pour pointer vers ceux de Cloudflare
   - ⚠️ **ATTENTION** : Cela peut prendre 24-48h pour se propager

### Étape 3 : Configurer les DNS dans Cloudflare

Une fois les nameservers mis à jour, ajouter ces enregistrements DNS dans Cloudflare :

| Type | Name | Content | Proxy | TTL |
|------|------|---------|-------|-----|
| A | @ | IP de Render | ✅ Proxied (orange) | Auto |
| A | www | IP de Render | ✅ Proxied (orange) | Auto |
| CNAME | www | ci-habiko.com | ✅ Proxied (orange) | Auto |

**Comment trouver l'IP de Render ?**
- Dans Render Dashboard → Service → Settings → Networking
- Ou utiliser `nslookup` : `nslookup ci-habiko.com`

### Étape 4 : Configuration SSL/TLS

1. Dans Cloudflare Dashboard → SSL/TLS
2. Mode : **Full (strict)** (recommandé)
3. Cloudflare génère automatiquement un certificat SSL
4. Render doit aussi avoir HTTPS configuré (déjà fait)

### Étape 5 : Configuration du Cache

1. Dans Cloudflare Dashboard → Caching → Configuration
2. **Niveau de cache** : Standard
3. **Purge du cache** : Utiliser "Purge Everything" si besoin après un déploiement

**Règles de cache recommandées** :
- Cache statique (CSS, JS, images) : 1 mois
- Pages HTML : 4 heures
- API endpoints : Pas de cache

### Étape 6 : Configuration de la Sécurité

1. **Firewall** :
   - Activer "Under Attack Mode" si nécessaire
   - Configurer des règles pour bloquer les bots malveillants

2. **Rate Limiting** (plan Pro requis) :
   - Limiter les requêtes par IP
   - Protéger les endpoints sensibles

3. **Bot Fight Mode** :
   - Activer pour bloquer les bots malveillants
   - ⚠️ Peut bloquer certains crawlers légitimes

### Étape 7 : Headers de Sécurité

Cloudflare ajoute automatiquement certains headers, mais Django doit aussi être configuré.

**Dans `kiaba/settings.py`** (déjà configuré) :
```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

**Headers Cloudflare à vérifier** :
- `CF-Connecting-IP` : IP réelle du client (au lieu de l'IP de Cloudflare)
- `CF-Ray` : ID de requête Cloudflare
- `CF-Visitor` : Protocole (http/https)

### Étape 8 : Configuration Render avec Cloudflare

**Dans Render Dashboard** :
1. Aller dans Settings → Networking
2. Vérifier que le domaine `ci-habiko.com` est bien configuré
3. Render doit accepter les requêtes depuis Cloudflare

**Important** : Avec Cloudflare, Render reçoit les requêtes depuis les IPs de Cloudflare, pas directement depuis les utilisateurs.

## 🔧 Configuration Django pour Cloudflare

### Middleware pour récupérer l'IP réelle

Créer un middleware pour utiliser `CF-Connecting-IP` :

```python
# core/middleware.py (à ajouter)

class CloudflareMiddleware:
    """
    Middleware pour récupérer l'IP réelle du client depuis Cloudflare
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Cloudflare envoie l'IP réelle dans ce header
        cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_connecting_ip:
            request.META['REMOTE_ADDR'] = cf_connecting_ip
        
        response = self.get_response(request)
        return response
```

### Configuration des headers de sécurité

Les headers suivants sont déjà configurés dans Django :
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: same-origin`

Cloudflare ajoute aussi :
- `CF-Cache-Status` : Statut du cache
- `CF-Ray` : ID de requête
- `Server: cloudflare`

## 📊 Analytics Cloudflare

Cloudflare fournit des analytics gratuits :
- Requêtes par pays
- Requêtes par type
- Bande passante utilisée
- Top pages
- Menaces bloquées

## ⚠️ Points d'attention

### 1. Cache et déploiements
- Après un déploiement, purger le cache Cloudflare si nécessaire
- Les assets statiques (CSS, JS) sont mis en cache, utiliser des versions (versioning)

### 2. Sessions Django
- Avec Cloudflare, l'IP peut changer
- Utiliser les cookies de session (déjà fait)

### 3. Rate Limiting
- Cloudflare limite automatiquement les requêtes abusives
- Peut affecter les crawlers légitimes (Google, etc.)
- Configurer des exceptions si nécessaire

### 4. WebSockets
- Si tu utilises WebSockets plus tard, configurer dans Cloudflare
- Actuellement pas nécessaire pour HABIKO

## 🚀 Checklist de déploiement

- [ ] Compte Cloudflare créé
- [ ] Nameservers mis à jour dans LWS Panel
- [ ] DNS configurés dans Cloudflare (A, CNAME)
- [ ] SSL/TLS en mode "Full (strict)"
- [ ] Cache configuré
- [ ] Firewall activé
- [ ] Middleware Cloudflare ajouté dans Django
- [ ] Headers de sécurité vérifiés
- [ ] Test de connexion depuis différents pays
- [ ] Analytics Cloudflare activés

## 📚 Ressources

- [Documentation Cloudflare](https://developers.cloudflare.com/)
- [Guide DNS Cloudflare](https://developers.cloudflare.com/dns/)
- [Guide SSL/TLS Cloudflare](https://developers.cloudflare.com/ssl/)
- [Guide Cache Cloudflare](https://developers.cloudflare.com/cache/)

## 💡 Astuces

1. **Plan Free** : Suffit pour commencer, limite à 100 règles de page
2. **Plan Pro** : $20/mois, rate limiting, analytics avancés
3. **Purge du cache** : Utiliser l'API Cloudflare pour purger automatiquement après déploiement
4. **Workers** : Cloudflare Workers peut être utilisé pour du edge computing (avancé)

## ✅ Résultat attendu

Une fois configuré :
- ✅ Site plus rapide grâce au CDN
- ✅ Protection DDoS automatique
- ✅ SSL/TLS gratuit et automatique
- ✅ Analytics détaillés
- ✅ Meilleure sécurité globale
- ✅ Réduction de la charge sur Render
