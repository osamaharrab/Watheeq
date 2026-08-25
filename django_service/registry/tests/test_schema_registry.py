from django.db import IntegrityError, transaction
from django.test import TestCase

from registry.models import SchemaRegistryState


class SchemaRegistryStateTests(TestCase):
    def test_migration_stores_schema_version_in_force(self):
        state = SchemaRegistryState.objects.get(pk=1)

        self.assertEqual(state.version, "watheeq-graph-1.0.0")

    def test_database_rejects_another_singleton_id(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SchemaRegistryState.objects.create(
                id=2,
                version="watheeq-graph-1.0.0",
            )
