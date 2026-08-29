"""Run provenance-preserving JSONL ingestion from an explicit source directory."""
from django.core.management.base import BaseCommand, CommandError

from registry.ingestion import ingest_seed


# Exposes provenance-preserving seed ingestion as a thin Django command.
class Command(BaseCommand):
    """Run provenance-preserving JSONL ingestion and report its accounting."""
    help = "Load JSONL seed records into the PostgreSQL ingestion ledger."

    # Requires callers to identify the directory containing source JSONL files.
    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            required=True,
            help="Directory containing the seed JSONL files.",
        )

    # Runs ingestion, prints reasons and counts, and fails on broken accounting.
    def handle(self, *args, **options):
        try:
            summary = ingest_seed(options["source"])
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        for source_file, counts in summary["files"].items():
            self.stdout.write(_summary_line(source_file, counts))
            for detail in counts["reasons"]:
                self.stdout.write(
                    "  line {line_number} {status}: {reason}".format(**detail)
                )

        self.stdout.write(_summary_line("overall", summary["total"]))

        files_reconcile = all(
            counts["reconciled"] for counts in summary["files"].values()
        )
        if not files_reconcile or not summary["total"]["reconciled"]:
            raise CommandError("Seed record accounting did not reconcile")


# Formats one file or overall result with the explicit reconciliation equation.
def _summary_line(label, counts):
    reconciled = "yes" if counts["reconciled"] else "no"
    return (
        f"{label}: read={counts['records_read']} "
        f"accepted={counts['accepted']} coerced={counts['coerced']} "
        f"quarantined={counts['quarantined']} rejected={counts['rejected']} "
        f"records_in_ledger={counts['records_in_ledger']} "
        f"accounting={counts['records_read']}={counts['records_in_ledger']}+"
        f"{counts['quarantined']}+{counts['rejected']} "
        f"reconciled={reconciled}"
    )
