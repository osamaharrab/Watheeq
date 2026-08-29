"""Small HTTP client for Django-owned audit persistence."""
from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings


class AuditUnavailable(Exception):
    """Raised when Django cannot accept the required audit record."""
    pass


class DjangoClient:
    """Use Django's internal API for audit persistence without direct PostgreSQL access."""
    def __init__(self, settings: Settings):
        self.http = httpx.Client(base_url=settings.django_base_url, timeout=settings.query_timeout_seconds)

    def close(self) -> None:
        """Close the local HTTP client."""
        self.http.close()

    def readiness(self) -> bool:
        """Check whether Django and its authoritative database are ready."""
        try:
            response = self.http.get("/ready")
            return response.is_success
        except httpx.HTTPError:
            return False

    def create_audit(self, payload: dict[str, Any]) -> None:
        """Persist an audit record and fail closed when Django rejects the write."""
        try:
            response = self.http.post("/internal/audit", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise AuditUnavailable("Django audit write failed") from error
