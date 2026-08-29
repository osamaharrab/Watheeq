"""Expose immutable audit replay as a Django management command."""
import json

from django.core.management.base import BaseCommand, CommandError

from registry.audit import replay_audit_record
from registry.models import QueryAudit


class Command(BaseCommand):
    """Print the stored response reconstructed from one audit record."""
    help = "Reconstruct a query response from its immutable audit row alone."

    def add_arguments(self, parser):
        parser.add_argument("--request-id", required=True)

    def handle(self, *args, **options):
        try:
            audit = QueryAudit.objects.get(request_id=options["request_id"])
        except (QueryAudit.DoesNotExist, ValueError) as exc:
            raise CommandError("Audit record not found") from exc

        self.stdout.write(
            json.dumps(
                replay_audit_record(audit),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
