"""Registry routes for internal audit writes and public audit or ledger reads."""
from django.urls import path

from .views import AuditDetailView, InternalAuditCreateView, LedgerEntityView


urlpatterns = [
    path("internal/audit", InternalAuditCreateView.as_view(), name="internal-audit-create"),
    path(
        "api/v1/audit/<uuid:request_id>",
        AuditDetailView.as_view(),
        name="audit-detail",
    ),
    path(
        "api/v1/ledger/entities/<str:entity_uid>",
        LedgerEntityView.as_view(),
        name="ledger-entity",
    ),
]
