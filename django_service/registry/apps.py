"""Django application configuration for the authoritative registry domain."""
from django.apps import AppConfig


class RegistryConfig(AppConfig):
    """Registers the registry models and API views with Django."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "registry"
