"""WSGI entry point for serving the Django registry service."""
import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "watheeq.settings")

application = get_wsgi_application()
