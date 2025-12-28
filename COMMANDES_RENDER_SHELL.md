# Commandes pour exécuter les migrations sur Render Shell

## Accès au Shell Render

1. Allez sur https://dashboard.render.com
2. Sélectionnez votre service web
3. Cliquez sur "Shell" dans le menu de gauche
4. Une fois connecté, vous êtes dans `/app`

## Commandes à exécuter

```bash
# 1. Vérifier les migrations en attente
python manage.py showmigrations

# 2. Créer les migrations (si nécessaire, mais normalement elles sont déjà créées)
python manage.py makemigrations accounts ads

# 3. Appliquer les migrations
python manage.py migrate

# 4. Vérifier que tout est appliqué
python manage.py showmigrations

# 5. (Optionnel) Créer les données initiales (packages de recharge et options de boost)
python manage.py create_recharge_packages
python manage.py create_boost_options
```

## Commandes complètes (copier-coller)

```bash
python manage.py migrate
python manage.py create_recharge_packages
python manage.py create_boost_options
```

## Vérification

Pour vérifier que les tables sont créées :

```bash
python manage.py dbshell
```

Puis dans PostgreSQL :
```sql
\dt accounts_*
\dt ads_*
\q
```


