"""Rebuild the small local Weaviate grounding index."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.neo4j import Neo4jClient
from app.clients.weaviate import WatheeqGrounding
from app.config import get_settings
from app.grounding import GroundingService, LocalEmbedder


def main() -> None:
    """Recreate local grounding vectors from Neo4j nodes and registry capabilities."""
    settings = get_settings()
    neo4j = Neo4jClient(settings)
    grounding = GroundingService(settings, neo4j, WatheeqGrounding(settings), LocalEmbedder(settings))
    try:
        # The index is derived data and can be rebuilt without touching PostgreSQL truth.
        print(json.dumps(grounding.rebuild(), sort_keys=True))
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
