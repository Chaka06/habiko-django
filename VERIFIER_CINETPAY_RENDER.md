# Vérifier la configuration CinetPay sur Render

## Problème : "Configuration CinetPay incomplète"

Cette erreur signifie que les variables d'environnement CinetPay ne sont pas chargées correctement.

## Solution 1 : Vérifier dans le Dashboard Render

1. Allez sur https://dashboard.render.com
2. Sélectionnez votre service web (kiaba-web)
3. Allez dans l'onglet **"Environment"** ou **"Environment Variables"**
4. Vérifiez que ces variables existent avec les bonnes valeurs :

```
CINETPAY_SITE_ID = 105907241
CINETPAY_API_KEY = 1317052651681a6fdef33a80.27918103
CINETPAY_SITE_KEY = 9694017766946fdd7c66b09.59234458
CINETPAY_NOTIFY_URL = https://ci-kiaba.com/accounts/payment/cinetpay/notify/
CINETPAY_RETURN_URL = https://ci-kiaba.com/accounts/payment/cinetpay/return/
```

5. Si elles n'existent pas, **ajoutez-les manuellement** dans le dashboard Render
6. **Redéployez** le service après avoir ajouté les variables

## Solution 2 : Vérifier via le Shell Render

Connectez-vous au shell Render et exécutez :

```bash
python manage.py shell
```

Puis dans le shell Python :

```python
from django.conf import settings
print("SITE_ID:", getattr(settings, "CINETPAY_SITE_ID", "MANQUANT"))
print("API_KEY:", getattr(settings, "CINETPAY_API_KEY", "MANQUANT")[:10] + "...")
print("SITE_KEY:", getattr(settings, "CINETPAY_SITE_KEY", "MANQUANT")[:10] + "...")
```

Si vous voyez "MANQUANT", les variables ne sont pas chargées.

## Solution 3 : Vérifier les logs Render

Dans les logs Render, cherchez les messages de debug qui commencent par "CinetPay config" pour voir quelles variables sont chargées.

## Important

- Les variables dans `render.yaml` sont utilisées lors du **premier déploiement** ou lors d'un **déploiement via blueprint**
- Si le service existe déjà, vous devez **ajouter les variables manuellement** dans le dashboard Render
- Après avoir ajouté/modifié des variables, **redéployez toujours le service**


