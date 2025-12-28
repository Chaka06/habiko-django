# 🔧 Solution : Navigateur qui force HTTPS automatiquement

## Problème
Quand vous tapez `http://localhost:8080`, le navigateur redirige automatiquement vers `https://localhost:8080` et cause une erreur SSL.

## Cause
Le navigateur a mémorisé une politique HSTS (HTTP Strict Transport Security) qui force HTTPS pour localhost.

## Solutions

### Solution 1 : Désactiver HSTS dans Chrome
1. Ouvrez Chrome
2. Allez sur : `chrome://net-internals/#hsts`
3. Dans la section **"Delete domain security policies"**
4. Entrez : `localhost`
5. Cliquez sur **"Delete"**
6. Entrez aussi : `127.0.0.1` et cliquez sur **"Delete"**
7. Fermez et rouvrez Chrome
8. Essayez : `http://localhost:8080`

### Solution 2 : Désactiver HSTS dans Firefox
1. Ouvrez Firefox
2. Allez sur : `about:config`
3. Acceptez les risques
4. Cherchez : `security.tls.insecure_fallback_hosts`
5. Double-cliquez et ajoutez : `localhost,127.0.0.1`
6. Redémarrez Firefox
7. Essayez : `http://localhost:8080`

### Solution 3 : Navigation privée
- Ouvrez une fenêtre de navigation privée/incognito
- Allez sur : `http://localhost:8080`
- Le cache HSTS ne s'applique pas en navigation privée

### Solution 4 : Utiliser un autre navigateur
- Safari, Edge, ou un autre navigateur qui n'a pas de cache HSTS pour localhost

### Solution 5 : Utiliser 127.0.0.1 au lieu de localhost
- Essayez : `http://127.0.0.1:8080`
- Parfois cela évite le cache HSTS de localhost

## Vérification
Après avoir appliqué une solution, vérifiez que :
- L'URL dans la barre d'adresse commence par `http://` (pas `https://`)
- Le site s'affiche correctement
- Pas d'erreur SSL

## Note
J'ai déjà désactivé HSTS dans les settings Django pour le développement. Le problème vient du cache du navigateur.

