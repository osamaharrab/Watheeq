import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.routes.ask import get_pipeline
from app.routes.entities import get_grounding, get_neo4j
from app.schemas import AskResponse


class FakePipeline:
    def ask(self, request):
        return AskResponse(status="unsupported", answer="outside slice"), "request-123"


class FakeGrounding:
    def resolve_entity(self, name):
        return [{"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "One", "metadata": {}, "match_method": "exact"}]


class FakeNeo4j:
    def __init__(self, exists=False):
        self.exists = exists

    def entity_exists(self, entity_uid):
        return self.exists

    def ownership_paths(self, entity_uid, as_of):
        return []


class ApiValidationTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides = {get_pipeline: lambda: FakePipeline(), get_grounding: lambda: FakeGrounding(), get_neo4j: lambda: FakeNeo4j()}
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides = {}

    def test_ask_validation_and_request_id_header(self):
        self.assertEqual(self.client.post("/api/v1/ask", json={"question": "x", "extra": True}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/ask", json={"question": ["x"]}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/ask", json={"question": "x", "as_of": "bad"}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/ask", json={"question": "x" * 2001}).status_code, 422)
        response = self.client.post("/api/v1/ask", json={"question": "x"})
        self.assertEqual(response.headers["X-Request-ID"], "request-123")
        self.assertNotIn("request_id", response.json())

    def test_body_size_entity_resolution_and_missing_ownership(self):
        response = self.client.post("/api/v1/ask", content=b"x" * 9000, headers={"content-length": "9000", "content-type": "application/json"})
        self.assertEqual(response.status_code, 413)
        entity = self.client.post("/api/v1/entities/resolve", json={"name": "One"})
        self.assertEqual(entity.json()["matches"][0]["canonical_id"], "LE-001")
        self.assertEqual(self.client.get("/api/v1/entities/LE-404/ownership").status_code, 404)

    def test_body_size_limit_applies_without_content_length_and_preserves_body(self):
        small = self.client.build_request(
            "POST",
            "/api/v1/entities/resolve",
            content=b'{"name":"One"}',
            headers={"content-type": "application/json", "content-length": "14"},
        )
        self.assertEqual(self.client.send(small).status_code, 200)

        headerless_small = self.client.build_request(
            "POST",
            "/api/v1/entities/resolve",
            content=b'{"name":"One"}',
            headers={"content-type": "application/json"},
        )
        del headerless_small.headers["content-length"]
        self.assertNotIn("content-length", headerless_small.headers)
        self.assertEqual(self.client.send(headerless_small).json()["matches"][0]["canonical_id"], "LE-001")

        headerless_large = self.client.build_request(
            "POST",
            "/api/v1/ask",
            content=b"x" * 9000,
            headers={"content-type": "application/json"},
        )
        del headerless_large.headers["content-length"]
        self.assertNotIn("content-length", headerless_large.headers)
        self.assertEqual(self.client.send(headerless_large).status_code, 413)

    def test_schema_endpoint_remains_available(self):
        response = self.client.get("/api/v1/schema")
        self.assertEqual(response.status_code, 200)
        self.assertIn("node_labels", response.json())
