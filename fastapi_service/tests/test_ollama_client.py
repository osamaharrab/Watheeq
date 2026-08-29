import unittest

import httpx

from app.clients.ollama import ModelUnavailable, OllamaClient, PlannerOutputError
from app.schemas import Text2CypherOutput

from tests.support import test_settings


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self.content}}


class FakeHttp:
    def __init__(self, content):
        self.content = content
        self.payloads = []

    def post(self, path, json):
        self.payloads.append((path, json))
        return FakeResponse(self.content)


class FailingHttp:
    def post(self, path, json):
        raise httpx.ConnectError("offline")


class OllamaClientTests(unittest.TestCase):
    def client(self, content):
        client = OllamaClient(test_settings())
        client.http = FakeHttp(content)
        return client

    def test_planner_uses_one_json_schema_call_with_structured_ownership_fields(self):
        client = self.client(
            '{"action":"query","query_kind":"incoming_ownership","answer_mode":"facts","holder_mentions":[],"target_mentions":["LE-005"],"cypher":"MATCH ...","reason":""}'
        )
        plan = client.generate_cypher("prompt")
        self.assertEqual(plan.query_kind, "incoming_ownership")
        self.assertEqual(plan.target_mentions, ["LE-005"])
        self.assertEqual(len(client.http.payloads), 1)
        payload = client.http.payloads[0][1]
        self.assertEqual(payload["format"], Text2CypherOutput.model_json_schema())
        self.assertFalse(payload["think"])
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertEqual(payload["options"]["seed"], test_settings().ollama_seed)

    def test_invalid_planner_json_is_a_planner_error(self):
        for content in (
            '{}',
            '{"action":"not-a-plan","reason":"bad action"}',
            'not json',
        ):
            with self.subTest(content=content), self.assertRaises(PlannerOutputError):
                self.client(content).generate_cypher("prompt")

    def test_http_failure_is_model_unavailable(self):
        client = OllamaClient(test_settings())
        client.http = FailingHttp()
        with self.assertRaises(ModelUnavailable):
            client.generate_cypher("prompt")
