"""Small Weaviate v3 client for rebuildable grounding documents."""
from __future__ import annotations

import json
from typing import Any

import weaviate

from ..config import Settings


class GroundingUnavailable(Exception):
    """Raised when the rebuildable grounding store cannot serve a request."""
    pass


class WatheeqGrounding:
    """Store and search explicit local vectors for entity and capability grounding."""
    class_name = "WatheeqGrounding"
    fields = [
        "doc_id",
        "kind",
        "node_type",
        "canonical_id",
        "display_name",
        "text",
        "metadata_json",
    ]

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = weaviate.Client(url=settings.weaviate_url)

    def ready(self) -> bool:
        """Check that the Weaviate service and grounding class are available."""
        try:
            return bool(self.client.is_ready()) and self.client.schema.exists(self.class_name)
        except Exception:
            return False

    def reset(self) -> None:
        """Replace the grounding class with the expected no-vectorizer schema."""
        try:
            if self.client.schema.exists(self.class_name):
                self.client.schema.delete_class(self.class_name)
            self.client.schema.create_class(
                {
                    "class": self.class_name,
                    "vectorizer": "none",
                    "properties": [
                        {"name": "doc_id", "dataType": ["text"]},
                        {"name": "kind", "dataType": ["text"]},
                        {"name": "node_type", "dataType": ["text"]},
                        {"name": "canonical_id", "dataType": ["text"]},
                        {"name": "display_name", "dataType": ["text"]},
                        {"name": "text", "dataType": ["text"]},
                        {"name": "metadata_json", "dataType": ["text"]},
                    ],
                }
            )
        except Exception as error:
            raise GroundingUnavailable("Weaviate collection reset failed") from error

    def add_documents(self, documents: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        """Insert pre-embedded entity or capability documents into Weaviate."""
        try:
            self.client.batch.configure(batch_size=50)
            with self.client.batch as batch:
                for document, vector in zip(documents, vectors, strict=True):
                    properties = {
                        "doc_id": document["doc_id"],
                        "kind": document["kind"],
                        "node_type": document.get("node_type", ""),
                        "canonical_id": document.get("canonical_id", ""),
                        "display_name": document.get("display_name", ""),
                        "text": document["text"],
                        "metadata_json": json.dumps(document.get("metadata", {}), sort_keys=True),
                    }
                    batch.add_data_object(properties, self.class_name, vector=vector)
        except Exception as error:
            raise GroundingUnavailable("Weaviate document insert failed") from error

    def search(self, kind: str, query: str, vector: list[float], limit: int) -> list[dict[str, Any]]:
        """Run bounded hybrid BM25-plus-vector search for one document kind."""
        try:
            result = (
                self.client.query.get(self.class_name, self.fields)
                .with_hybrid(query=query, vector=vector, alpha=self.settings.grounding_alpha)
                .with_where({"path": ["kind"], "operator": "Equal", "valueText": kind})
                .with_additional(["score"])
                .with_limit(limit)
                .do()
            )
            rows = result.get("data", {}).get("Get", {}).get(self.class_name, [])
            normalized = []
            for row in rows:
                metadata = row.get("metadata_json", "{}")
                normalized.append(
                    {
                        "doc_id": row.get("doc_id", ""),
                        "kind": row.get("kind", ""),
                        "node_type": row.get("node_type", ""),
                        "canonical_id": row.get("canonical_id", ""),
                        "display_name": row.get("display_name", ""),
                        "text": row.get("text", ""),
                        "metadata": json.loads(metadata),
                        "score": row.get("_additional", {}).get("score", 0),
                    }
                )
            return normalized
        except Exception as error:
            raise GroundingUnavailable("Weaviate hybrid search failed") from error
