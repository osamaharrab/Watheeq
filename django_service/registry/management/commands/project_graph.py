"""Run the explicit rebuild of the derived Neo4j ownership projection."""
from django.core.management.base import BaseCommand, CommandError

from registry.graph_projection import project_graph


# Exposes the ownership graph rebuild as a thin Django command.
class Command(BaseCommand):
    """Rebuild the Neo4j ownership projection from PostgreSQL."""
    help = "Rebuild the Neo4j ownership graph from PostgreSQL."

    def handle(self, *args, **options):
        try:
            counts = project_graph()
        except Exception as exc:
            raise CommandError(f"Graph projection failed: {exc}") from exc

        self.stdout.write("Projected graph:")
        self.stdout.write(f"LegalEntity: {counts['LegalEntity']}")
        self.stdout.write(f"NaturalPerson: {counts['NaturalPerson']}")
        self.stdout.write(
            f"HOLDS_INTEREST_IN: {counts['HOLDS_INTEREST_IN']}"
        )
