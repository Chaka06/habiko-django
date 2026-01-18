# RAPPORT DE COHÉRENCE DU SYSTÈME D'EMAILS HABIKO

Date: 2026-01-18
Analysé par: Sub-Agent Verdent

## RÉSUMÉ EXÉCUTIF

Le système d'emails de HABIKO présente plusieurs incohérences critiques entre les appels dans le code Python et les templates disponibles. Des corrections sont nécessaires pour assurer le bon fonctionnement.

---

## 1. ANALYSE DES APPELS À EmailService.send_email

### 1.1 accounts/tasks.py

#### ✅ send_account_created_email (ligne 81-156)
- **Template appelé**: `"account_created"`
- **Chemin recherché**: `account_created.html` + `account_created.txt`
- **Chemin réel**: `templates/account/email/account_created.html` + `.txt`
- **Statut**: ⚠️ **INCOHÉRENCE - Chemin manquant**
- **Problème**: Le template est appelé sans le préfixe `account/email/`
- **Variables utilisées**: `user`, `confirmation_url`, `site_url`
- **Correction requise**: Changer `"account_created"` → `"account/email/account_created"`

#### ❌ send_ad_published_email (ligne 167-196)
- **Template appelé**: `"account/email/ad_published"`
- **Chemin recherché**: `account/email/ad_published.html` + `.txt`
- **Chemin réel**: `templates/account/email/ad_published.html` existe mais **PAS de .txt correspondant**
- **Statut**: ⚠️ **INCOHÉRENCE - Fichier .txt manquant**
- **Problème**: Il existe `ad_published_message.txt` mais EmailService cherche `ad_published.txt`
- **Variables utilisées**: `user`, `ad`, `site_name`, `site_url`, `ad_url`
- **Correction requise**: Renommer `ad_published_message.txt` → `ad_published.txt`

#### ❌ send_login_notification_email (ligne 199-230)
- **Template appelé**: `"account/email/login_notification"`
- **Chemin recherché**: `account/email/login_notification.html` + `.txt`
- **Chemin réel**: `templates/account/email/login_notification.html` existe mais **PAS de .txt correspondant**
- **Statut**: ⚠️ **INCOHÉRENCE - Fichier .txt manquant**
- **Problème**: Il existe `login_notification_message.txt` mais EmailService cherche `login_notification.txt`
- **Variables utilisées**: `user`, `site_name`, `site_url`
- **Correction requise**: Renommer `login_notification_message.txt` → `login_notification.txt`

#### ❌ send_password_change_email (ligne 241-268)
- **Template appelé**: `"account/email/password_change"`
- **Chemin recherché**: `account/email/password_change.html` + `.txt`
- **Chemin réel**: `templates/account/email/password_change.html` existe mais **PAS de .txt correspondant**
- **Statut**: ⚠️ **INCOHÉRENCE - Fichier .txt manquant**
- **Problème**: Il existe `password_change_message.txt` mais EmailService cherche `password_change.txt`
- **Variables utilisées**: `user`, `site_name`, `site_url`
- **Correction requise**: Renommer `password_change_message.txt` → `password_change.txt`

#### ❌ send_ad_expiration_email (ligne 279-308)
- **Template appelé**: `"account/email/ad_expiration"`
- **Chemin recherché**: `account/email/ad_expiration.html` + `.txt`
- **Chemin réel**: `templates/account/email/ad_expiration.html` existe mais **PAS de .txt correspondant**
- **Statut**: ⚠️ **INCOHÉRENCE - Fichier .txt manquant**
- **Problème**: Il existe `ad_expiration_message.txt` mais EmailService cherche `ad_expiration.txt`
- **Variables utilisées**: `user`, `ad`, `site_name`, `site_url`, `ad_url`
- **Correction requise**: Renommer `ad_expiration_message.txt` → `ad_expiration.txt`

---

### 1.2 accounts/views.py

#### ✅ password_change_otp (ligne 80-90 et 149-159)
- **Template appelé**: `"account/email/password_change_otp"`
- **Chemin recherché**: `account/email/password_change_otp.html` + `.txt`
- **Chemin réel**: `templates/account/email/password_change_otp.html` + `.txt` ✅
- **Statut**: ✅ **COHÉRENT**
- **Variables utilisées**: `user`, `code`, `site_url`

---

### 1.3 ads/tasks.py

#### ❌ send_moderation_notification (ligne 67-112)
- **Templates appelés**: 
  - Approuvé: `"account/email/ad_approved"`
  - Rejeté: `"account/email/ad_rejected"`
- **Chemin recherché**: 
  - `account/email/ad_approved.html` + `.txt`
  - `account/email/ad_rejected.html` + `.txt`
- **Chemin réel**: Les deux paires existent ✅
- **Statut**: ✅ **COHÉRENT**
- **Variables utilisées**: `user`, `ad`, `ad_url`, `reason`

#### ✅ auto_approve_ad (ligne 45-63)
- **Appelle**: `send_ad_published_email.delay(ad.id)` → voir problème dans 1.1

---

### 1.4 ads/admin_views.py

#### ✅ approve_ad / reject_ad (lignes 11-65)
- **Appelle**: `send_moderation_notification.delay()` → voir 1.3

---

### 1.5 core/views.py

#### ✅ post / edit_ad (lignes 30-332)
- **Appelle**: `send_ad_published_email.delay(ad.id)` → voir problème dans 1.1

---

### 1.6 accounts/adapters.py (Allauth Integration)

#### ✅ email_confirmation
- **Template appelé**: `account/email/email_confirmation`
- **Fichiers**: `.html`, `_message.txt`, `_subject.txt` ✅
- **Statut**: ✅ **COHÉRENT**

#### ✅ password_reset
- **Template appelé**: `account/email/password_reset`
- **Fichiers**: `.html`, `_message.txt`, `_subject.txt` ✅
- **Statut**: ✅ **COHÉRENT**

---

## 2. TEMPLATES EXISTANTS JAMAIS UTILISÉS

### ❌ Templates orphelins (avec suffix `_message.txt`)

Ces templates ne seront JAMAIS trouvés par EmailService.send_email car il cherche `.txt` directement:

1. **ad_published_message.txt** → doit être renommé `ad_published.txt`
2. **login_notification_message.txt** → doit être renommé `login_notification.txt`
3. **password_change_message.txt** → doit être renommé `password_change.txt`
4. **ad_expiration_message.txt** → doit être renommé `ad_expiration.txt`

### ✅ Templates utilisés correctement par Allauth

- `email_confirmation_message.txt` + `email_confirmation_subject.txt` (via adapters.py)
- `password_reset_message.txt` + `password_reset_subject.txt` (via adapters.py)

---

## 3. VARIABLES MANQUANTES DANS LE CONTEXTE

### ✅ Tous les contextes semblent complets

Tous les appels fournissent les variables nécessaires selon les templates HTML examinés.

---

## 4. FONCTIONNEMENT DU SYSTÈME EmailService

D'après `accounts/email_service.py` (lignes 88-95):

```python
if template_name:
    try:
        html_content = render_to_string(f"{template_name}.html", context)
        text_content = render_to_string(f"{template_name}.txt", context)
    except Exception as e:
        logger.warning(f"Template {template_name} non trouvé...")
```

**Comportement**:
- EmailService ajoute automatiquement `.html` et `.txt` au `template_name`
- Il cherche dans `TEMPLATE_DIRS` configuré dans Django
- Si le template n'est pas trouvé, il utilise le `text_content` fourni en paramètre (fallback)

**Exemple**:
- Appel: `template_name="account/email/ad_published"`
- Cherche: `account/email/ad_published.html` ✅ (existe)
- Cherche: `account/email/ad_published.txt` ❌ (n'existe pas, il y a `ad_published_message.txt`)

---

## 5. PROBLÈMES CRITIQUES IDENTIFIÉS

### Problème #1: Incohérence de nommage des fichiers .txt

**Gravité**: 🔴 **CRITIQUE**

**Description**: 
4 templates `.txt` utilisent le suffix `_message.txt` alors que EmailService cherche directement `.txt`

**Impact**:
- Les emails envoyés n'auront PAS de version texte
- Seule la version HTML sera envoyée
- Problèmes de délivrabilité (détection spam)
- Utilisateurs sans HTML ne verront rien

**Fichiers concernés**:
1. `ad_published_message.txt` → renommer en `ad_published.txt`
2. `login_notification_message.txt` → renommer en `login_notification.txt`
3. `password_change_message.txt` → renommer en `password_change.txt`
4. `ad_expiration_message.txt` → renommer en `ad_expiration.txt`

### Problème #2: Chemin incomplet dans send_account_created_email

**Gravité**: 🟡 **MOYEN**

**Description**: 
Le template est appelé avec `"account_created"` au lieu de `"account/email/account_created"`

**Impact**:
- Le template ne sera jamais trouvé
- Fallback sur le `text_content` défini en dur dans le code (lignes 109-136)
- Le template HTML magnifiquement conçu ne sera jamais utilisé

**Fichier concerné**: `accounts/tasks.py` ligne 142

**Correction**:
```python
# AVANT
template_name="account_created",

# APRÈS
template_name="account/email/account_created",
```

---

## 6. RECOMMANDATIONS

### 6.1 Corrections immédiates (PRIORITÉ 1)

1. **Renommer les fichiers .txt** pour correspondre au système de nommage:
   ```bash
   mv templates/account/email/ad_published_message.txt templates/account/email/ad_published.txt
   mv templates/account/email/login_notification_message.txt templates/account/email/login_notification.txt
   mv templates/account/email/password_change_message.txt templates/account/email/password_change.txt
   mv templates/account/email/ad_expiration_message.txt templates/account/email/ad_expiration.txt
   ```

2. **Corriger le chemin dans send_account_created_email**:
   ```python
   template_name="account/email/account_created",  # ligne 142 de accounts/tasks.py
   ```

### 6.2 Améliorations futures (PRIORITÉ 2)

1. **Créer un test automatisé** qui vérifie:
   - Tous les appels à EmailService.send_email ont des templates correspondants
   - Tous les templates HTML ont un équivalent .txt
   - Tous les contextes contiennent les variables requises

2. **Standardiser la convention de nommage**:
   - Soit: `{nom}.html` + `{nom}.txt` (actuel pour EmailService)
   - Soit: `{nom}.html` + `{nom}_message.txt` + `{nom}_subject.txt` (Allauth)
   - **Recommandation**: Garder les deux selon l'usage:
     - Allauth: `_message.txt` + `_subject.txt`
     - EmailService direct: `.txt` uniquement

3. **Ajouter une validation des contextes**:
   ```python
   # Dans EmailService.send_email
   required_vars = get_template_required_vars(template_name)
   missing_vars = set(required_vars) - set(context.keys())
   if missing_vars:
       logger.warning(f"Variables manquantes: {missing_vars}")
   ```

---

## 7. SYNTHÈSE DES FICHIERS À MODIFIER

### Fichiers Python à corriger:

1. **accounts/tasks.py** (ligne 142)
   ```python
   template_name="account/email/account_created",
   ```

### Fichiers templates à renommer:

1. `templates/account/email/ad_published_message.txt` → `ad_published.txt`
2. `templates/account/email/login_notification_message.txt` → `login_notification.txt`
3. `templates/account/email/password_change_message.txt` → `password_change.txt`
4. `templates/account/email/ad_expiration_message.txt` → `ad_expiration.txt`

---

## 8. CHECKLIST DE VALIDATION

- [ ] Renommer les 4 fichiers .txt
- [ ] Corriger le chemin dans send_account_created_email
- [ ] Tester l'envoi de chaque type d'email
- [ ] Vérifier la réception HTML + texte
- [ ] Tester avec un client email texte uniquement
- [ ] Vérifier les logs pour les warnings de templates

---

## CONCLUSION

Le système d'emails est **fonctionnel mais incomplet**. Les problèmes identifiés sont principalement:

1. 🔴 **4 templates .txt mal nommés** → versions texte jamais utilisées
2. 🟡 **1 chemin de template incomplet** → template HTML jamais utilisé

**Impact utilisateur**: 
- Emails envoyés mais sans version texte optimale
- Risque accru de détection spam
- Expérience dégradée pour utilisateurs sans HTML

**Temps de correction estimé**: 15 minutes

**Priorité**: HAUTE (affecte la délivrabilité des emails)
