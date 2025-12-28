# Déboguer les erreurs Bad Gateway intermittentes

## Problème
Parfois, même en rechargeant une page, vous obtenez une erreur "Bad Gateway" sur Render.

## Causes possibles

### 1. Problème avec le profil utilisateur
- **Symptôme** : Erreur quand on accède à `user.profile` alors qu'il n'existe pas
- **Solution** : ✅ Corrigé - Le dashboard crée maintenant automatiquement le profil s'il n'existe pas

### 2. Problème avec les migrations
- **Symptôme** : Erreur lors de l'accès à des modèles qui n'existent pas encore
- **Solution** : Exécuter les migrations dans le shell Render :
  ```bash
  python manage.py migrate
  ```

### 3. Problème avec les signaux
- **Symptôme** : Erreur lors de la création d'un utilisateur
- **Solution** : ✅ Corrigé - Le signal ne crée plus d'Account automatiquement

### 4. Problème avec les context processors
- **Symptôme** : Erreur dans le context processor `site_metrics`
- **Solution** : ✅ Déjà géré avec try/except

### 5. Problème avec les middlewares
- **Symptôme** : Erreur dans un middleware qui bloque la requête
- **Solution** : Vérifier les logs Render pour voir quel middleware cause le problème

## Comment déboguer

### 1. Vérifier les logs Render
1. Allez sur https://dashboard.render.com
2. Sélectionnez votre service web
3. Ouvrez l'onglet **"Logs"**
4. Cherchez les erreurs récentes (lignes en rouge)
5. Notez l'heure exacte de l'erreur

### 2. Vérifier les erreurs Python
Dans les logs, cherchez :
- `Traceback (most recent call last)`
- `AttributeError`
- `DoesNotExist`
- `OperationalError`

### 3. Tester dans le shell Render
```bash
# Se connecter au shell Render
python manage.py shell
```

```python
# Tester l'accès au profil
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.first()
print("User:", user)
print("Has profile:", hasattr(user, 'profile'))
if hasattr(user, 'profile'):
    print("Profile:", user.profile)
```

### 4. Vérifier les migrations
```bash
python manage.py showmigrations
python manage.py migrate
```

## Solutions appliquées

✅ **Dashboard** : Crée automatiquement le profil s'il n'existe pas
✅ **Template dashboard** : Gestion sécurisée de `user.profile` avec vérifications
✅ **Signal create_profile** : Ne crée plus d'Account automatiquement

## Si le problème persiste

1. **Vérifier les logs Render** pour l'erreur exacte
2. **Partager les logs** avec l'heure exacte de l'erreur
3. **Vérifier si c'est spécifique à certaines pages** (dashboard, post, etc.)

## Commandes utiles

```bash
# Vérifier l'état de l'application
python manage.py check

# Vérifier les migrations
python manage.py showmigrations

# Appliquer les migrations
python manage.py migrate

# Vérifier la configuration
python manage.py shell
>>> from django.conf import settings
>>> print(settings.DEBUG)
```


