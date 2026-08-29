"""Central runtime configuration."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_MAX_QUESTION_CHARS = 2000


class Settings(BaseSettings):
    """Loads the small set of local-service settings used by the query slice."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    django_base_url: str = "http://django:8000"
    graph_db_uri: str = "bolt://neo4j:7687"
    graph_db_user: str = "neo4j"
    # Neo4j credentials must come from the environment, never from source defaults.
    graph_db_password: str
    weaviate_url: str = "http://weaviate:8080"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_model_digest: str = "dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364"
    ollama_timeout_seconds: int = 120
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    grounding_alpha: float = 0.5
    grounding_top_k: int = 5
    max_query_depth: int = 4
    max_query_results: int = 100
    query_timeout_seconds: int = 3
    max_question_chars: int = DEFAULT_MAX_QUESTION_CHARS
    max_request_body_bytes: int = 8192
    ollama_seed: int = 7
    ollama_max_tokens: int = 500


@lru_cache
def get_settings() -> Settings:
    """Reuse one validated settings object for the FastAPI process."""
    return Settings()
