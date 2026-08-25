from pydantic import BaseModel


class SchemaResponse(BaseModel):
    schema_version: str
    conventions: dict[str, str]
    node_labels: dict[str, list[str]]
    relationship_types: dict[str, dict[str, list[str]]]
    not_represented: list[str]
