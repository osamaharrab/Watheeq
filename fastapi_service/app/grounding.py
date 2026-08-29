"""Local embeddings and the small rebuildable grounding index."""
from __future__ import annotations

import unicodedata
import re
from typing import Any

from sentence_transformers import SentenceTransformer

from .clients.neo4j import Neo4jClient
from .clients.weaviate import WatheeqGrounding
from .config import Settings
from .schema_registry import get_queryable_schema


class LocalEmbedder:
    """Creates local MiniLM vectors for the rebuildable Weaviate index."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = SentenceTransformer(settings.embedding_model, local_files_only=True)

    def encode_one(self, text: str) -> list[float]:
        """Embed one query or entity string and enforce the configured dimension."""
        vector = self.model.encode(text, normalize_embeddings=True).tolist()
        self._check_dimension(vector)
        return vector

    def encode_many(self, texts: list[str]) -> list[list[float]]:
        """Embed rebuild documents in one local model call."""
        vectors = self.model.encode(texts, normalize_embeddings=True).tolist()
        for vector in vectors:
            self._check_dimension(vector)
        return vectors

    def _check_dimension(self, vector: list[float]) -> None:
        if len(vector) != self.settings.embedding_dimensions:
            raise ValueError("Embedding dimension does not match configuration")


class GroundingService:
    """Resolve supported entities and prepare small schema-capability context."""
    def __init__(self, settings: Settings, neo4j: Neo4jClient, store: WatheeqGrounding, embedder: LocalEmbedder):
        self.settings = settings
        self.neo4j = neo4j
        self.store = store
        self.embedder = embedder

    def resolve_entity(self, value: str) -> list[dict[str, Any]]:
        # Exact Neo4j matches are authoritative; hybrid search is only a fallback.
        normalized = unicodedata.normalize("NFKC", value).strip()
        exact = self.neo4j.resolve_exact(normalized)
        if exact:
            return self._ordered(exact)
        candidates = self.store.search(
            "entity", normalized, self.embedder.encode_one(normalized), self.settings.grounding_top_k
        )
        return self._verify(candidates, "hybrid")

    def entity_candidates(self, question: str) -> list[dict[str, Any]]:
        """Find question entities, preferring explicit IDs and exact names."""
        normalized = unicodedata.normalize("NFKC", question).strip()
        identifiers = sorted(set(match.upper() for match in re.findall(r"\b(?:LE|NP)-\d+\b", normalized, flags=re.IGNORECASE)))
        if identifiers:
            # Never replace an unknown explicit ID with an unrelated hybrid candidate.
            matches = []
            for identifier in identifiers:
                matches.extend(self.neo4j.resolve_exact(identifier))
            return self._ordered(matches)
        candidates = self.store.search(
            "entity", question, self.embedder.encode_one(question), self.settings.grounding_top_k
        )
        question_text = normalized.casefold()
        exact_names = sorted(
            {
                candidate["display_name"]
                for candidate in candidates
                if candidate.get("display_name")
                and unicodedata.normalize("NFKC", candidate["display_name"]).strip().casefold() in question_text
            }
        )
        if exact_names:
            # Legal names may be duplicated, so keep every exact Neo4j match.
            matches = []
            for name in exact_names:
                matches.extend(self.neo4j.resolve_exact(name))
            return self._ordered(matches)
        return self._verify(candidates, "hybrid")

    def question_context(self, question: str) -> list[dict[str, str]]:
        """Retrieve capability notes only; Weaviate is not business truth."""
        candidates = self.store.search(
            "capability", question, self.embedder.encode_one(question), self.settings.grounding_top_k
        )
        return [
            {"doc_id": candidate["doc_id"], "text": candidate["text"]}
            for candidate in sorted(candidates, key=lambda item: item["doc_id"])
        ]

    def rebuild(self) -> dict[str, int]:
        """Recreate entity and capability grounding documents from local sources."""
        entities = [self._entity_document(entity) for entity in self.neo4j.grounding_nodes()]
        capabilities = self._capability_documents()
        documents = entities + capabilities
        vectors = self.embedder.encode_many([document["text"] for document in documents])
        self.store.reset()
        self.store.add_documents(documents, vectors)
        return {"entities": len(entities), "capabilities": len(capabilities), "documents": len(documents)}

    def _verify(self, candidates: list[dict[str, Any]], method: str) -> list[dict[str, Any]]:
        # Weaviate discovers candidates, but the Neo4j projection confirms they exist.
        verified: list[dict[str, Any]] = []
        for candidate in candidates:
            canonical_id = candidate.get("canonical_id", "")
            node_type = candidate.get("node_type", "")
            for match in self.neo4j.resolve_exact(canonical_id):
                if match["canonical_id"] == canonical_id and match["type"] == node_type:
                    verified.append({**match, "match_method": method})
        return self._ordered(verified)

    @staticmethod
    def _ordered(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate typed identities and return a stable response order."""
        unique = {(match["type"], match["canonical_id"]): match for match in matches}
        return [unique[key] for key in sorted(unique)]

    @staticmethod
    def _entity_document(entity: dict[str, Any]) -> dict[str, Any]:
        """Build one small grounding document from a projected supported node."""
        metadata = entity.get("metadata", {})
        detail = " ".join(str(value) for value in metadata.values() if value)
        return {
            "doc_id": f"entity:{entity['type']}:{entity['canonical_id']}",
            "kind": "entity",
            "node_type": entity["type"],
            "canonical_id": entity["canonical_id"],
            "display_name": entity["display_name"],
            "metadata": metadata,
            "text": " ".join(part for part in [entity["display_name"], entity["canonical_id"], detail] if part),
        }

    @staticmethod
    def _capability_documents() -> list[dict[str, Any]]:
        """Describe the queryable slice without indexing raw ledger or eval data."""
        schema = get_queryable_schema()
        unsupported = ", ".join(str(item) for item in schema.get("not_represented", []))
        texts = [
            ("capability:ownership", "The queryable graph supports LegalEntity and NaturalPerson with HOLDS_INTEREST_IN ownership facts only."),
            ("capability:dates", "Current ownership means valid_to is null. Historical ownership needs structured as_of and uses inclusive valid_from and valid_to bounds."),
            ("capability:scope", "Asset, instrument, unit, pledge, and other graph relationship questions are unsupported in this ownership slice."),
            ("capability:not-represented", f"The following information is not represented by the query service: {unsupported}."),
        ]
        return [
            {
                "doc_id": doc_id,
                "kind": "capability",
                "node_type": "",
                "canonical_id": "",
                "display_name": "",
                "metadata": {},
                "text": text,
            }
            for doc_id, text in texts
        ]
