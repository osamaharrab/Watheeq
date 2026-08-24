from django.core.management.base import BaseCommand, CommandError

from registry.reconciliation import reconcile_projection


# Exposes the read-only projection comparison as a thin Django command.
class Command(BaseCommand):
    help = "Check whether the Neo4j ownership graph matches PostgreSQL."

    def handle(self, *args, **options):
        try:
            result = reconcile_projection()
        except Exception as exc:
            raise CommandError(f"Projection reconciliation failed: {exc}") from exc

        self.stdout.write("Reconciliation:")
        self._write_result("LegalEntity", result["LegalEntity"])
        self._write_result("NaturalPerson", result["NaturalPerson"])
        self._write_result(
            "HOLDS_INTEREST_IN",
            result["HOLDS_INTEREST_IN"],
        )

        if not result["reconciled"]:
            self.stdout.write("reconciled: no")
            raise CommandError("Neo4j projection does not match PostgreSQL")

        self.stdout.write("reconciled: yes")

    def _write_result(self, label, counts):
        status = "OK" if counts["matches"] else "MISMATCH"
        self.stdout.write(
            f"{label}: {counts['actual']}/{counts['expected']} {status}"
        )
