# Déboguer les erreurs CinetPay

## Erreur : "Une erreur s'est produite, votre paiement a échoué"

### Étapes de débogage

1. **Vérifier les logs Render** :
   - Allez sur https://dashboard.render.com
   - Sélectionnez votre service web
   - Ouvrez l'onglet "Logs"
   - Cherchez les lignes contenant "CinetPay" ou "paiement"
   - Les logs montreront :
     - Les données envoyées à CinetPay
     - La réponse complète de CinetPay
     - Les erreurs détaillées

2. **Vérifier la configuration** :
   ```bash
   # Dans le shell Render
   python manage.py shell
   ```
   ```python
   from django.conf import settings
   print("SITE_ID:", getattr(settings, "CINETPAY_SITE_ID", "MANQUANT"))
   print("API_KEY:", getattr(settings, "CINETPAY_API_KEY", "MANQUANT")[:10] + "...")
   ```

3. **Vérifier les URLs de callback** :
   - Les URLs `notify_url` et `return_url` doivent être accessibles publiquement
   - Vérifiez que `https://ci-kiaba.com/accounts/payment/cinetpay/notify/` est accessible
   - Vérifiez que `https://ci-kiaba.com/accounts/payment/cinetpay/return/` est accessible

4. **Vérifier le format du montant** :
   - Le montant doit être un entier (pas de décimales)
   - Pour 4000 FCFA, le montant doit être `4000` (pas `4000.00`)

5. **Vérifier dans le dashboard CinetPay** :
   - Connectez-vous à votre compte CinetPay
   - Vérifiez les transactions en attente/échouées
   - Regardez les détails de l'erreur dans le dashboard

## Erreurs courantes

### "Configuration CinetPay incomplète"
- **Cause** : Variables d'environnement manquantes
- **Solution** : Ajouter les variables dans le dashboard Render

### "Erreur CinetPay: [message]"
- **Cause** : Erreur retournée par l'API CinetPay
- **Solution** : Vérifier le message d'erreur dans les logs et le dashboard CinetPay

### "URL de paiement non trouvée"
- **Cause** : Format de réponse inattendu du SDK
- **Solution** : Vérifier les logs pour voir la réponse complète

## Tester manuellement

Dans le shell Render :

```python
from accounts.cinetpay import CinetPayService
from accounts.models import Transaction, RechargePackage
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
package = RechargePackage.objects.first()

# Créer une transaction de test
transaction = Transaction.objects.create(
    user=user,
    transaction_type=Transaction.TransactionType.RECHARGE,
    amount=package.amount,
    status=Transaction.Status.PENDING,
    recharge_package=package,
    description=f"Test Recharge {package.name}",
)

# Tester l'initialisation
try:
    url = CinetPayService.create_payment_link(
        transaction,
        package.amount,
        f"Test {package.name}"
    )
    print(f"Succès! URL: {url}")
except Exception as e:
    print(f"Erreur: {e}")
```


