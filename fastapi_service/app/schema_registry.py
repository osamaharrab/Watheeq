import json
from pathlib import Path
from typing import Any


AUTHORITATIVE_REGISTRY_PATH = Path("/app/reference/graph_schema_registry.json")

IMPLEMENTED_NODE_LABELS = (
    "LegalEntity",
    "NaturalPerson",
)

IMPLEMENTED_RELATIONSHIP_TYPES = (
    "HOLDS_INTEREST_IN",
)


class SchemaRegistryError(ValueError):
    pass


def load_authoritative_registry(
    registry_path: str | Path = AUTHORITATIVE_REGISTRY_PATH,
) -> dict[str, Any]:
    path = Path(registry_path)
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SchemaRegistryError(
            f"Schema registry file not found: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise SchemaRegistryError(
            f"Schema registry contains invalid JSON: {path}"
        ) from exc
    except OSError as exc:
        raise SchemaRegistryError(f"Schema registry could not be read: {path}") from exc

    if not isinstance(registry, dict):
        raise SchemaRegistryError("Schema registry must be a JSON object")

    schema_version = registry.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise SchemaRegistryError(
            "Schema registry schema_version must be a non-empty string"
        )

    conventions = registry.get("conventions")
    if not isinstance(conventions, dict) or not all(
        isinstance(name, str) and isinstance(description, str)
        for name, description in conventions.items()
    ):
        raise SchemaRegistryError(
            "Schema registry conventions must be an object of strings"
        )

    node_labels = registry.get("node_labels")
    if not isinstance(node_labels, dict):
        raise SchemaRegistryError("Schema registry node_labels must be an object")
    for label in IMPLEMENTED_NODE_LABELS:
        if label not in node_labels:
            raise SchemaRegistryError(
                f"Schema registry is missing node label {label}"
            )
        properties = node_labels[label]
        if not isinstance(properties, list) or not all(
            isinstance(property_name, str) for property_name in properties
        ):
            raise SchemaRegistryError(
                f"Schema registry node label {label} must contain a property list"
            )

    relationship_types = registry.get("relationship_types")
    if not isinstance(relationship_types, dict):
        raise SchemaRegistryError(
            "Schema registry relationship_types must be an object"
        )
    for relationship_type in IMPLEMENTED_RELATIONSHIP_TYPES:
        if relationship_type not in relationship_types:
            raise SchemaRegistryError(
                f"Schema registry is missing relationship type {relationship_type}"
            )
        definition = relationship_types[relationship_type]
        if not isinstance(definition, dict):
            raise SchemaRegistryError(
                f"Schema registry relationship {relationship_type} must be an object"
            )
        for field_name in ("from", "to", "properties"):
            value = definition.get(field_name)
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise SchemaRegistryError(
                    f"Schema registry relationship {relationship_type} "
                    f"must contain a {field_name} list"
                )

    not_represented = registry.get("not_represented")
    if not isinstance(not_represented, list) or not all(
        isinstance(item, str) for item in not_represented
    ):
        raise SchemaRegistryError("Schema registry not_represented must be a list")

    return registry


def get_queryable_schema() -> dict[str, Any]:
    registry = load_authoritative_registry()

    node_labels = {
        name: registry["node_labels"][name]
        for name in IMPLEMENTED_NODE_LABELS
    }
    relationship_types = {
        name: registry["relationship_types"][name]
        for name in IMPLEMENTED_RELATIONSHIP_TYPES
    }

    return {
        "schema_version": registry["schema_version"],
        "conventions": registry["conventions"],
        "node_labels": node_labels,
        "relationship_types": relationship_types,
        "not_represented": registry["not_represented"],
    }
