"""Separate Django process liveness from PostgreSQL dependency readiness."""
from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Reports that the Django process can serve requests."""
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # Liveness intentionally does not require a database connection.
        return Response({"status": "ok", "service": "django"})


class ReadyView(APIView):
    """Reports whether the authoritative PostgreSQL dependency is reachable."""
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # A small query verifies the configured database connection without changing data.
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:
            return Response(
                {
                    "status": "not_ready",
                    "service": "django",
                    "dependencies": {"postgres": "unavailable"},
                    "error": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "status": "ready",
                "service": "django",
                "dependencies": {"postgres": "ok"},
            }
        )
