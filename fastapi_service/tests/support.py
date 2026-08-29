from app.config import Settings


def test_settings(**overrides):
    values = {
        "django_base_url": "http://django.test",
        "graph_db_uri": "bolt://neo4j.test:7687",
        "graph_db_user": "neo4j",
        "graph_db_password": "password",
        "weaviate_url": "http://weaviate.test:8080",
        "ollama_url": "http://ollama.test:11434",
        "ollama_timeout_seconds": 120,
        "max_query_depth": 4,
        "max_query_results": 3,
        "query_timeout_seconds": 3,
    }
    values.update(overrides)
    return Settings(**values)
