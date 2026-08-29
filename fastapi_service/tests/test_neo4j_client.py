import unittest
from unittest.mock import MagicMock, patch

from neo4j import Query, READ_ACCESS
from neo4j.exceptions import Neo4jError
from neo4j.graph import Relationship
from neo4j.time import Date as Neo4jDate

from app.clients.neo4j import GraphUnavailable, Neo4jClient, QueryBoundedError, _serialize

from tests.support import test_settings


class FakeSession:
    def __init__(self, result=None, error=None):
        self.result = result or []
        self.error = error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def run(self, query, parameters):
        self.calls.append((query, parameters))
        if self.error:
            raise self.error
        return self.result


class FakeDriver:
    def __init__(self, session):
        self.session_object = session
        self.kwargs = None

    def session(self, **kwargs):
        self.kwargs = kwargs
        return self.session_object

    def close(self):
        pass


class FakeNode(dict):
    def __init__(self, labels, **properties):
        super().__init__(properties)
        self.labels = set(labels)


class FakeRelationship(dict):
    def __init__(self, **properties):
        super().__init__(properties)


class FakePath:
    def __init__(self, nodes, relationships):
        self.nodes = nodes
        self.relationships = relationships


class Neo4jClientTests(unittest.TestCase):
    def client(self, session):
        driver = FakeDriver(session)
        with patch("app.clients.neo4j.GraphDatabase.driver", return_value=driver):
            return Neo4jClient(test_settings()), driver

    def test_read_access_query_timeout_and_parameters(self):
        session = FakeSession([{"value": 1}])
        client, driver = self.client(session)
        self.assertEqual(client.execute_read("RETURN 1 AS value", {"entity_uids": ["LE-001"]}), [{"value": 1}])
        self.assertEqual(driver.kwargs["default_access_mode"], READ_ACCESS)
        query, parameters = session.calls[0]
        self.assertIsInstance(query, Query)
        self.assertEqual(query.timeout, 3)
        self.assertEqual(parameters, {"entity_uids": ["LE-001"]})

    def test_result_bound_and_driver_errors(self):
        bounded, _ = self.client(FakeSession([{"x": 1}, {"x": 2}, {"x": 3}, {"x": 4}]))
        with self.assertRaises(QueryBoundedError):
            bounded.execute_read("RETURN 1 AS x")
        timeout, _ = self.client(FakeSession(error=Neo4jError("timed out")))
        with self.assertRaises(QueryBoundedError):
            timeout.execute_read("RETURN 1 AS x")
        unavailable, _ = self.client(FakeSession(error=Neo4jError("connection failed")))
        with self.assertRaises(GraphUnavailable):
            unavailable.execute_read("RETURN 1 AS x")
        connection, _ = self.client(FakeSession(error=ConnectionError("socket closed")))
        with self.assertRaises(GraphUnavailable):
            connection.execute_read("RETURN 1 AS x")

    def test_exact_resolution_shape(self):
        session = FakeSession([{"type": "LegalEntity", "canonical_id": "LE-001", "display_name": "One", "metadata": {}}])
        client, _ = self.client(session)
        match = client.resolve_exact("LE-001")[0]
        self.assertEqual(match["canonical_id"], "LE-001")
        self.assertEqual(match["match_method"], "exact")

    def test_ownership_paths_use_one_simple_shape(self):
        person = FakeNode(["NaturalPerson"], person_uid="NP-001", full_name="Person")
        entity = FakeNode(["LegalEntity"], entity_uid="LE-001", legal_name="Entity")
        relation = FakeRelationship(bps=5000, valid_from="2024-01-01", valid_to=None, filing_uid="F-001")
        client, _ = self.client(FakeSession())
        client._run = MagicMock(return_value=[{"path": FakePath([person, entity], [relation])}])
        path = client.ownership_paths("LE-001", None)[0]
        self.assertEqual(path["nodes"][0]["canonical_id"], "NP-001")
        self.assertEqual(path["relationships"][0]["held_entity_uid"], "LE-001")

    def test_ownership_path_preserves_null_filing_uid(self):
        person = FakeNode(["NaturalPerson"], person_uid="NP-001", full_name="Person")
        entity = FakeNode(["LegalEntity"], entity_uid="LE-001", legal_name="Entity")
        relation = FakeRelationship(bps=5000, valid_from="2024-01-01", valid_to=None, filing_uid=None)
        client, _ = self.client(FakeSession())
        client._run = MagicMock(return_value=[{"path": FakePath([person, entity], [relation])}])
        self.assertIsNone(client.ownership_paths("LE-001", None)[0]["relationships"][0]["filing_uid"])

    def test_relationship_serialization_keeps_endpoints(self):
        relationship = MagicMock(spec=Relationship)
        relationship.type = "HOLDS_INTEREST_IN"
        relationship.start_node = MagicMock()
        relationship.end_node = MagicMock()
        relationship.keys.return_value = []
        serialized = _serialize(relationship)
        self.assertEqual(serialized["type"], "HOLDS_INTEREST_IN")
        self.assertIn("start", serialized)
        self.assertIn("end", serialized)

    def test_neo4j_dates_are_json_safe_in_nested_values(self):
        value = Neo4jDate(2024, 1, 1)
        self.assertEqual(_serialize(value), "2024-01-01")
        self.assertEqual(_serialize({"dates": [value]}), {"dates": ["2024-01-01"]})
