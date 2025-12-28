from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Configure le site Django après le chargement"""
        # Le Site Django est maintenant configuré via setup_site.py dans le startCommand
        # Cela évite d'accéder à la base de données pendant l'initialisation de l'app
        # et élimine le warning "Accessing the database during app initialization"
        pass
