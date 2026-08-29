"""ASGI entry point for serving the Django registry service."""
import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watheeq.settings")

application = get_asgi_application()
