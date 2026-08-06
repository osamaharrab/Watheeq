"""Environment configuration for the FastAPI query service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    django_base_url: str
    graph_db_uri: str
    graph_db_user: str
    graph_db_password: str
    weaviate_url: str
    ollama_url: str
    ollama_model: str
    ollama_model_digest: str


def get_settings() -> Settings:
    return Settings(
        django_base_url=os.environ["DJANGO_BASE_URL"],
        graph_db_uri=os.environ["GRAPH_DB_URI"],
        graph_db_user=os.environ["GRAPH_DB_USER"],
        graph_db_password=os.environ["GRAPH_DB_PASSWORD"],
        weaviate_url=os.environ["WEAVIATE_URL"],
        ollama_url=os.environ["OLLAMA_URL"],
        ollama_model=os.environ["OLLAMA_MODEL"],
        ollama_model_digest=os.environ["OLLAMA_MODEL_DIGEST"],
    )
