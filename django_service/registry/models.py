from django.db import models


# Stores the single authoritative schema registry version currently in force.
class SchemaRegistryState(models.Model):
    id = models.PositiveSmallIntegerField(
        primary_key=True,
        default=1,
        editable=False,
    )
    version = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(id=1),
                name="schema_registry_state_singleton_id",
            )
        ]


# Preserves one source line and its ingestion outcome for complete accounting.
class IngestionRecord(models.Model):
    # Defines the four outcomes reported by the seed loader.
    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        COERCED = "coerced", "Coerced"
        QUARANTINED = "quarantined", "Quarantined"
        REJECTED = "rejected", "Rejected"

    source_file = models.CharField(max_length=255)
    line_number = models.PositiveIntegerField()
    record_type = models.CharField(max_length=64)
    raw_payload = models.JSONField()
    status = models.CharField(max_length=16, choices=Status.choices)
    reason = models.TextField(blank=True)

    # Prevents a repeated load from creating another ledger row for the same line.
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_file", "line_number"],
                name="unique_ingestion_source_line",
            )
        ]


# Stores one legal entity identified by the authoritative entity UID.
class LegalEntity(models.Model):
    entity_uid = models.CharField(max_length=64, primary_key=True)
    legal_name = models.TextField()
    legal_name_ar = models.TextField(null=True, blank=True)
    jurisdiction = models.CharField(max_length=2)
    registration_no = models.CharField(max_length=100)
    incorporation_date = models.DateField()
    status = models.CharField(max_length=50)
    status_as_of = models.DateField()


# Stores one natural person identified by the authoritative person UID.
class NaturalPerson(models.Model):
    person_uid = models.CharField(max_length=64, primary_key=True)
    full_name = models.TextField()
    full_name_ar = models.TextField(null=True, blank=True)
    nationality = models.CharField(max_length=2)
    dob_year = models.IntegerField()


# Stores one filing and the filing links present in filings.jsonl.
class Filing(models.Model):
    filing_uid = models.CharField(max_length=64, primary_key=True)
    filing_type = models.CharField(max_length=100)
    filed_on = models.DateField()
    source_registry = models.CharField(max_length=100)
    asserts_about = models.ForeignKey(
        LegalEntity,
        on_delete=models.PROTECT,
        related_name="filings",
    )
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="superseded_by",
    )


# Stores one effective-dated person-or-entity ownership interest in a legal entity.
class OwnershipInterest(models.Model):
    holder_person = models.ForeignKey(
        NaturalPerson,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ownership_interests",
    )
    holder_entity = models.ForeignKey(
        LegalEntity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="held_ownership_interests",
    )
    held_entity = models.ForeignKey(
        LegalEntity,
        on_delete=models.PROTECT,
        related_name="ownership_interests",
    )
    bps = models.IntegerField()
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    filing = models.ForeignKey(
        Filing,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ownership_interests",
    )
    provenance = models.OneToOneField(
        IngestionRecord,
        on_delete=models.PROTECT,
        related_name="ownership_interest",
    )

    # Enforces that each ownership interest has one and only one holder type.
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(holder_person__isnull=False, holder_entity__isnull=True)
                    | models.Q(holder_person__isnull=True, holder_entity__isnull=False)
                ),
                name="ownership_has_exactly_one_holder",
            )
        ]
