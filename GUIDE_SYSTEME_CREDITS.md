# Guide : Système de Crédits et Boosts

## 📋 Vue d'ensemble

Le système de crédits permet aux utilisateurs de :
- Recharger leur compte avec différentes formules
- Poster des annonces (nécessite des crédits sauf pour les nouveaux comptes)
- Booster leurs annonces (Premium, Urgent, Prolongation)

## 🆕 Nouveaux Comptes

**Les nouveaux utilisateurs ont droit à :**
- ✅ **2 annonces gratuites**
- ✅ **1 booster gratuit** (pour booster une de leurs 2 premières annonces)

## 💰 Formules de Recharge

### Pack 4000 FCFA
- **3 annonces** incluses
- **4000 FCFA** de crédit pour booster

### Pack 6000 FCFA
- **5 annonces** incluses
- **6000 FCFA** de crédit pour booster

### Pack 10000 FCFA
- **8 annonces** incluses
- **10000 FCFA** de crédit pour booster

### Pack 15000 FCFA
- **10 annonces** incluses
- **15000 FCFA** de crédit pour booster
- **2 boosters gratuits** sur les 2 premières annonces

### Pack Premium 20000 FCFA
- **15 annonces premium** incluses
- Toutes les annonces apparaissent **en tête de liste** de leur catégorie
- Compte marqué comme premium

## 🚀 Options de Boost

### Premium (Annonce en tête de liste)
- 3 jours : **1000 FCFA**
- 7 jours : **2900 FCFA**
- 15 jours : **5800 FCFA**
- 30 jours : **8100 FCFA**
- 45 jours : **15700 FCFA**
- 60 jours : **20300 FCFA**
- 90 jours : **30800 FCFA**

### Prolongation
- +45 jours : **1600 FCFA**
- +90 jours : **2900 FCFA**
- +180 jours : **5500 FCFA**
- +365 jours : **30100 FCFA**

### Urgent (Logo urgent)
- 7 jours : **2600 FCFA**
- 15 jours : **4200 FCFA**
- 30 jours : **7200 FCFA**

## 🔧 Installation

### 1. Créer les migrations

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### 2. Créer les formules de recharge

```bash
python manage.py create_recharge_packages
```

### 3. Créer les options de boost

```bash
python manage.py create_boost_options
```

## 💳 Intégration CinetPay

### Configuration

1. **Obtenir les clés API CinetPay** :
   - Site ID
   - API Key
   - Site Key

2. **Ajouter dans `settings.py`** :
```python
CINETPAY_SITE_ID = env("CINETPAY_SITE_ID")
CINETPAY_API_KEY = env("CINETPAY_API_KEY")
CINETPAY_SITE_KEY = env("CINETPAY_SITE_KEY")
CINETPAY_NOTIFY_URL = "https://ci-kiaba.com/payment/cinetpay/notify/"
CINETPAY_RETURN_URL = "https://ci-kiaba.com/payment/cinetpay/return/"
```

3. **URLs de callback** :
   - Notify URL : `/payment/cinetpay/notify/` (pour les notifications serveur)
   - Return URL : `/payment/cinetpay/return/` (pour le retour utilisateur)

## 📝 Utilisation

### Pour l'utilisateur

1. **Poster une annonce** :
   - Si nouveau compte : 2 annonces gratuites
   - Sinon : Doit recharger son compte

2. **Recharger le compte** :
   - Choisir une formule
   - Payer via CinetPay
   - Les crédits sont ajoutés automatiquement

3. **Booster une annonce** :
   - Choisir le type de boost (Premium, Urgent, Prolongation)
   - Choisir la durée
   - Payer avec le solde ou utiliser un booster gratuit

## 🔍 Modèles Créés

### Account
- `balance` : Solde en FCFA
- `free_ads_remaining` : Annonces gratuites restantes
- `ads_remaining` : Annonces du pack restantes
- `is_premium` : Compte premium
- `premium_ads_remaining` : Annonces premium restantes
- `free_boosters_remaining` : Boosters gratuits restants

### RechargePackage
- Formules de recharge (4000, 6000, 10000, 15000, 20000 FCFA)

### BoostOption
- Options de boost (Premium, Prolongation, Urgent)

### Transaction
- Historique des transactions (recharges, boosts)

### Ad (modifié)
- `is_premium` : Annonce premium
- `premium_until` : Date jusqu'à laquelle l'annonce est premium
- `is_urgent` : Annonce urgente
- `urgent_until` : Date jusqu'à laquelle l'annonce est urgente
- `extended_until` : Date de prolongation

## 🎯 Logique de Tri

Les annonces sont triées par :
1. **Premium** (en premier)
2. **Urgent** (ensuite)
3. **Date de création** (plus récentes en premier)

## ⚠️ Notes Importantes

- Les nouveaux comptes ont automatiquement 2 annonces gratuites
- Les annonces premium apparaissent en tête de liste de leur catégorie
- Les boosters gratuits ne peuvent être utilisés qu'une fois
- Le solde peut être utilisé pour booster les annonces
- Les transactions sont enregistrées pour traçabilité

## 📞 Support

Pour toute question sur le système de crédits, contactez l'administrateur.


