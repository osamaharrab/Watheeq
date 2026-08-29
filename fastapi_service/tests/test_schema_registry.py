import json
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schema_registry import (
    SchemaRegistryError,
    get_queryable_schema,
    load_authoritative_registry,
)


class SchemaRegistryTests(unittest.TestCase):
    def test_authoritative_registry_loads(self):
        registry = load_authoritative_registry()

        self.assertEqual(registry["schema_version"], "watheeq-graph-1.0.0")

    def test_runtime_node_slice_contains_only_implemented_labels(self):
        runtime = get_queryable_schema()

        self.assertEqual(
            set(runtime["node_labels"]),
            {"LegalEntity", "NaturalPerson"},
        )

    def test_runtime_relationship_slice_contains_only_ownership(self):
        runtime = get_queryable_schema()

        self.assertEqual(
            set(runtime["relationship_types"]),
            {"HOLDS_INTEREST_IN"},
        )

    def test_runtime_definitions_come_from_authoritative_registry(self):
        authoritative = load_authoritative_registry()
        runtime = get_queryable_schema()

        self.assertEqual(
            runtime["node_labels"]["LegalEntity"],
            authoritative["node_labels"]["LegalEntity"],
        )
        self.assertEqual(
            runtime["node_labels"]["NaturalPerson"],
            authoritative["node_labels"]["NaturalPerson"],
        )
        self.assertEqual(
            runtime["relationship_types"]["HOLDS_INTEREST_IN"],
            authoritative["relationship_types"]["HOLDS_INTEREST_IN"],
        )

    def test_unsupported_graph_elements_are_hidden(self):
        runtime = get_queryable_schema()

        for label in ("AssetUnit", "Instrument"):
            self.assertNotIn(label, runtime["node_labels"])
        for relationship_type in (
            "CONTROLS_ASSET",
            "PLEDGED_TO",
            "HOLDS_UNITS",
        ):
            self.assertNotIn(
                relationship_type,
                runtime["relationship_types"],
            )

    def test_missing_ownership_data_raises_clear_error(self):
        malformed_registry = {
            "schema_version": "watheeq-graph-1.0.0",
            "conventions": {},
            "node_labels": {"LegalEntity": []},
            "relationship_types": {
                "HOLDS_INTEREST_IN": {
                    "from": ["LegalEntity"],
                    "to": ["LegalEntity"],
                    "properties": [],
                }
            },
            "not_represented": [],
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
        ) as registry_file:
            json.dump(malformed_registry, registry_file)
            registry_file.flush()

            with self.assertRaisesRegex(SchemaRegistryError, "NaturalPerson"):
                load_authoritative_registry(registry_file.name)


class SchemaEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_schema_endpoint_returns_ownership_slice(self):
        response = self.client.get("/api/v1/schema")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["schema_version"], "watheeq-graph-1.0.0")
        self.assertEqual(
            set(body["node_labels"]),
            {"LegalEntity", "NaturalPerson"},
        )
        self.assertEqual(
            set(body["relationship_types"]),
            {"HOLDS_INTEREST_IN"},
        )

    def test_health_endpoint_still_works(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch("app.main.OllamaClient")
    @patch("app.main.WatheeqGrounding")
    @patch("app.main.Neo4jClient")
    @patch("app.main.DjangoClient")
    def test_ready_returns_200_when_dependencies_are_ready(
        self,
        django_client,
        neo4j_client,
        grounding,
        ollama_client,
    ):
        django_client.return_value.readiness.return_value = True
        neo4j_client.return_value.ready.return_value = True
        grounding.return_value.ready.return_value = True
        ollama_client.return_value.ready.return_value = True

        response = self.client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("app.main.OllamaClient")
    @patch("app.main.WatheeqGrounding")
    @patch("app.main.Neo4jClient")
    @patch("app.main.DjangoClient")
    def test_ready_returns_503_when_a_dependency_is_unavailable(
        self,
        django_client,
        neo4j_client,
        grounding,
        ollama_client,
    ):
        django_client.return_value.readiness.return_value = True
        neo4j_client.return_value.ready.return_value = False
        grounding.return_value.ready.return_value = True
        ollama_client.return_value.ready.return_value = True

        response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertFalse(response.json()["checks"]["neo4j"])
