import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.config import Settings


class SettingsTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_graph_password_is_required_and_accepts_an_explicit_value(self):
        settings = Settings(graph_db_password="test-only-password", _env_file=None)

        self.assertEqual(settings.graph_db_password, "test-only-password")
        self.assertEqual(settings.graph_db_uri, "bolt://neo4j:7687")
        self.assertEqual(settings.graph_db_user, "neo4j")
        self.assertTrue(Settings.model_fields["graph_db_password"].is_required())

    @patch.dict(os.environ, {}, clear=True)
    def test_graph_password_cannot_be_omitted(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None)
