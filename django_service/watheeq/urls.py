"""Top-level Django routes for health checks, audit, and ledger access."""
from django.urls import include, path

from watheeq.health import HealthView, ReadyView


urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("ready", ReadyView.as_view(), name="ready"),
    path("", include("registry.urls")),
]
