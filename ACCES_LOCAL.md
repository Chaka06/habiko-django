# 🌐 Accès au Site HABIKO en Local

## ⚠️ IMPORTANT : Utilisez HTTP (pas HTTPS)

Le serveur de développement utilise **HTTP uniquement**, pas HTTPS.

### ✅ URL CORRECTE
```
http://localhost:8080
```

### ❌ URL INCORRECTE (causera l'erreur SSL)
```
https://localhost:8080  ← NE PAS UTILISER
```

## 📋 Pages Disponibles

1. **Page d'accueil** : http://localhost:8080
2. **Liste des annonces** : http://localhost:8080/ads
3. **Connexion** : http://localhost:8080/auth/login/
4. **Inscription** : http://localhost:8080/auth/signup/
5. **Publier une annonce** : http://localhost:8080/post/ (nécessite connexion)
6. **Dashboard** : http://localhost:8080/dashboard/ (nécessite connexion)
7. **Admin Django** : http://localhost:8080/admin/

## 🔧 Si vous voyez l'erreur SSL

1. **Vérifiez l'URL** : Elle doit commencer par `http://` (pas `https://`)
2. **Videz le cache** : 
   - Mac : Cmd+Shift+R
   - Windows/Linux : Ctrl+Shift+R
3. **Navigation privée** : Essayez en mode incognito
4. **Réécrivez l'URL** : Tapez manuellement `http://localhost:8080`

## 🚀 Démarrer le Serveur

```bash
cd /Users/mac.chaka/Desktop/HABIKO
source .venv/bin/activate
export DEBUG=True DB_ENGINE=sqlite
python manage.py runserver 0.0.0.0:8080
```

## ✅ Vérifier que le Serveur Fonctionne

```bash
curl http://localhost:8080
```

Si vous voyez du HTML, le serveur fonctionne !

