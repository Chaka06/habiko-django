# Passer CinetPay en mode Production

## Problème
Vous êtes actuellement en mode TEST, ce qui signifie que les transactions ne sont pas réelles.

## Solution

### 1. Vérifier vos clés API dans le dashboard CinetPay

1. Connectez-vous à votre compte CinetPay : https://www.cinetpay.com
2. Allez dans **"Paramètres"** ou **"API"**
3. Vérifiez que vous utilisez les **clés de PRODUCTION** et non les clés de TEST

### 2. Clés API de Production vs Test

- **Mode TEST** : Les clés commencent souvent par "test_" ou sont dans un environnement séparé
- **Mode PRODUCTION** : Les clés sont celles de votre compte marchand réel

### 3. Vérifier dans le dashboard Render

Assurez-vous que vos variables d'environnement contiennent les **vraies clés de production** :

```
CINETPAY_SITE_ID = 105907241
CINETPAY_API_KEY = 1317052651681a6fdef33a80.27918103
CINETPAY_SITE_KEY = 9694017766946fdd7c66b09.59234458
CINETPAY_MODE = PRODUCTION
```

### 4. Activer le compte en production dans CinetPay

1. Dans votre dashboard CinetPay
2. Vérifiez que votre compte est **activé** et **approuvé** pour la production
3. Certains comptes nécessitent une validation manuelle avant de pouvoir traiter des paiements réels

### 5. Vérifier les URLs de callback

Les URLs doivent être accessibles publiquement et en HTTPS :
- `https://ci-kiaba.com/accounts/payment/cinetpay/notify/`
- `https://ci-kiaba.com/accounts/payment/cinetpay/return/`

### 6. Redéployer après modification

Après avoir mis à jour les clés API dans Render, **redéployez** le service.

## Comment savoir si vous êtes en mode TEST ?

- Les transactions apparaissent dans le dashboard CinetPay mais ne sont pas réelles
- Les paiements échouent avec des erreurs génériques
- Vous voyez "mode test" dans les logs ou le dashboard

## Important

⚠️ **Ne mélangez jamais les clés de test et de production !**
- Utilisez les clés de TEST uniquement pour le développement local
- Utilisez les clés de PRODUCTION uniquement sur votre site en ligne


