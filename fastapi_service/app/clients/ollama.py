"""Direct local Ollama calls for constrained generation."""
from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from ..config import Settings
from ..schemas import Text2CypherOutput


class ModelUnavailable(Exception):
    """Raised when the configured local Ollama service cannot be reached."""
    pass


class PlannerOutputError(Exception):
    """Raised when Ollama responds but does not provide a valid planner result."""
    pass


class OllamaClient:
    """Call the configured local model for a constrained ownership plan and Cypher."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.http = httpx.Client(base_url=settings.ollama_url, timeout=settings.ollama_timeout_seconds)

    def close(self) -> None:
        """Close the local HTTP client."""
        self.http.close()

    def ready(self) -> bool:
        """Require the configured model name and exact digest during readiness checks."""
        try:
            response = self.http.get("/api/tags")
            response.raise_for_status()
            for model in response.json().get("models", []):
                if model.get("name") == self.settings.ollama_model:
                    return model.get("digest") == self.settings.ollama_model_digest
            return False
        except httpx.HTTPError:
            return False

    def generate_cypher(self, prompt: str) -> Text2CypherOutput:
        """Request and validate the constrained Text2Cypher JSON response."""
        payload = self._chat(prompt)
        try:
            return Text2CypherOutput.model_validate(json.loads(payload))
        except (json.JSONDecodeError, ValidationError) as error:
            raise PlannerOutputError("Ollama returned invalid Text2Cypher JSON") from error

    def _chat(self, prompt: str) -> str:
        """Send one deterministic non-streaming local chat request."""
        try:
            response = self.http.post(
                "/api/chat",
                json={
                    "model": self.settings.ollama_model,
                    "stream": False,
                    "format": Text2CypherOutput.model_json_schema(),
                    "think": False,
                    "options": {
                        "temperature": 0,
                        "seed": self.settings.ollama_seed,
                        "num_predict": self.settings.ollama_max_tokens,
                    },
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            try:
                content = response.json().get("message", {}).get("content")
            except (TypeError, ValueError) as error:
                raise PlannerOutputError("Ollama response is not valid JSON") from error
            if not isinstance(content, str):
                raise PlannerOutputError("Ollama response has no message content")
            return content
        except httpx.HTTPError as error:
            raise ModelUnavailable("Configured local Ollama model is unavailable") from error
