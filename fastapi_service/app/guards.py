"""Conservative validation for the deliberately narrow generated Cypher surface."""
from __future__ import annotations

import re
from typing import Any


class CypherGuardError(ValueError):
    """Raised when untrusted generated Cypher leaves the approved read surface."""
    pass


FORBIDDEN = {
    "CREATE", "MERGE", "DELETE", "DETACH", "SET", "REMOVE", "DROP", "ALTER",
    "CALL", "LOAD", "FOREACH", "APOC", "SHOW", "USE", "PROFILE", "EXPLAIN",
    "UNION", "UNWIND", "WITH",
}
# The two mixed-holder patterns are the only approved unlabeled holder exceptions.
NODE = re.compile(r"\((?P<variable>[A-Za-z_]\w*)\s*:\s*(?P<label>[A-Za-z_]\w*)\s*\)")
RELATIONSHIP = re.compile(
    r"\((?P<left>[A-Za-z_]\w*)\s*:\s*(?P<left_label>[A-Za-z_]\w*)\s*\)"
    r"\s*-\[\s*(?P<variable>[A-Za-z_]\w*)?\s*:\s*(?P<type>[A-Za-z_]\w*)"
    r"(?:\*(?P<depth>\d+\.\.\d+))?\s*\]->\s*"
    r"\((?P<right>[A-Za-z_]\w*)\s*:\s*(?P<right_label>[A-Za-z_]\w*)\s*\)"
)
MIXED_HOLDER_PATH = re.compile(
    r"\((?P<holder>holder)\)\s*-\[\s*:\s*HOLDS_INTEREST_IN\*(?P<depth>\d+\.\.\d+)\s*\]->\s*"
    r"\((?P<target>target)\s*:\s*LegalEntity\s*\)"
)
MIXED_HOLDER_DIRECT = re.compile(
    r"\((?P<holder>holder)\)\s*-\[\s*(?P<relationship>rel)\s*:\s*HOLDS_INTEREST_IN\s*\]->\s*"
    r"\((?P<target>target)\s*:\s*LegalEntity\s*\)"
)
PROPERTY = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b")
PARAMETER = re.compile(r"\$([A-Za-z_]\w*)")


def _mask_data_text(cypher: str) -> str:
    """Hide quoted data and comments before checking executable Cypher clauses."""
    quoted_or_comment = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|//[^\n]*|/\*.*?\*/", re.DOTALL)
    return quoted_or_comment.sub(lambda match: " " * len(match.group(0)), cypher)


def _properties(schema: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Build per-label and per-relationship property allowlists from the registry."""
    node_properties = {label: set(properties) for label, properties in schema["node_labels"].items()}
    relationship_properties = {
        relationship: set(definition["properties"])
        for relationship, definition in schema["relationship_types"].items()
    }
    return node_properties, relationship_properties


def validate_cypher(
    cypher: str,
    schema: dict[str, Any],
    *,
    as_of: str | None,
    max_depth: int,
    max_results: int,
) -> None:
    """Allow only deterministic, bounded, read-only Cypher for this ownership slice."""
    masked = _mask_data_text(cypher)
    upper = masked.upper()
    # One MATCH/RETURN statement keeps generated queries easy to bound and audit.
    if ";" in masked or not re.search(r"\bMATCH\b", upper) or not re.search(r"\bRETURN\b", upper):
        raise CypherGuardError("Cypher must contain one MATCH/RETURN statement")
    if not re.search(r"\bORDER\s+BY\b", upper):
        raise CypherGuardError("Cypher must order results deterministically")
    if any(re.search(rf"\b{keyword}\b", upper) for keyword in FORBIDDEN):
        raise CypherGuardError("Cypher contains a forbidden clause")
    if "HOLDS_INTEREST_IN" in upper and re.search(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", cypher):
        raise CypherGuardError("Ownership queries must use runtime parameters, not inline values")
    if re.search(r"[:][A-Za-z_][\w]*[|&]|:[!%]", masked):
        raise CypherGuardError("Cypher label expressions are not allowed")
    if re.search(r"\{\s*[A-Za-z_]\w*\s*:", masked):
        raise CypherGuardError("Inline Cypher maps are not allowed")
    limits = re.findall(r"\bLIMIT\s+(\d+)\b", upper)
    if len(limits) != 1 or int(limits[0]) > max_results:
        raise CypherGuardError("Cypher requires one bounded literal LIMIT")

    # Bind each property reference to its declared node or relationship type.
    nodes, relationships = _properties(schema)
    node_variables: dict[str, str] = {}
    relationship_variables: dict[str, str] = {}
    mixed_holder = MIXED_HOLDER_PATH.search(masked)
    mixed_holder_direct = MIXED_HOLDER_DIRECT.search(masked)
    for match in NODE.finditer(masked):
        variable, label = match.group("variable"), match.group("label")
        if label not in nodes:
            raise CypherGuardError("Cypher uses an unsupported node label")
        node_variables[variable] = label
    for match in RELATIONSHIP.finditer(masked):
        relationship_type = match.group("type")
        if relationship_type not in relationships:
            raise CypherGuardError("Cypher uses an unsupported relationship type")
        depth = match.group("depth")
        if "*" in match.group(0) and depth is None:
            raise CypherGuardError("Variable-length traversal must be bounded")
        if depth and int(depth.split("..", 1)[1]) > max_depth:
            raise CypherGuardError("Traversal exceeds the configured depth")
        if relationship_type == "HOLDS_INTEREST_IN" and (
            match.group("left_label") not in {"LegalEntity", "NaturalPerson"}
            or match.group("right_label") != "LegalEntity"
        ):
            raise CypherGuardError("HOLDS_INTEREST_IN has invalid endpoint labels")
        if match.group("variable"):
            relationship_variables[match.group("variable")] = relationship_type

    if mixed_holder:
        depth = int(mixed_holder.group("depth").split("..", 1)[1])
        if depth > max_depth or not re.search(r"\(holder:LegalEntity\s+OR\s+holder:NaturalPerson\)", masked):
            raise CypherGuardError("Mixed ownership holders need the approved type constraint")
        node_variables["target"] = "LegalEntity"
        relationship_variables["rel"] = "HOLDS_INTEREST_IN"
    if mixed_holder_direct:
        if not re.search(r"\(holder:LegalEntity\s+OR\s+holder:NaturalPerson\)", masked):
            raise CypherGuardError("Mixed direct ownership holders need the approved type constraint")
        # A role-aware holder predicate may reference the two supported holder IDs.
        node_variables["holder"] = "MixedHolder"
        node_variables["target"] = "LegalEntity"
        relationship_variables["rel"] = "HOLDS_INTEREST_IN"
    if not node_variables or re.search(r"\(\s*[A-Za-z_]\w*\s*\)", masked) and not (mixed_holder or mixed_holder_direct):
        raise CypherGuardError("Every node pattern requires a supported label")
    if "-[" in masked and not RELATIONSHIP.search(masked) and not (mixed_holder or mixed_holder_direct):
        raise CypherGuardError("Every relationship pattern requires a supported type and direction")

    allowed_variables = {**node_variables, **relationship_variables}
    for variable, property_name in PROPERTY.findall(masked):
        if variable not in allowed_variables:
            raise CypherGuardError("Cypher uses an unknown property alias")
        if variable == "holder" and node_variables.get(variable) == "MixedHolder":
            allowed = nodes["LegalEntity"] | nodes["NaturalPerson"]
        else:
            allowed = nodes[allowed_variables[variable]] if variable in node_variables else relationships[allowed_variables[variable]]
        if property_name not in allowed:
            raise CypherGuardError("Cypher uses a property outside its schema type")
    if not set(PARAMETER.findall(masked)).issubset({"holder_uids", "target_uids", "as_of"}):
        raise CypherGuardError("Cypher uses an unsupported parameter")

    if "HOLDS_INTEREST_IN" in upper:
        # Current facts have no end date; historical end dates are inclusive.
        if as_of is None and not re.search(r"\bVALID_TO\s+IS\s+NULL\b", upper):
            raise CypherGuardError("Current ownership queries require valid_to IS NULL")
        if as_of is not None:
            ownership_aliases = [
                alias
                for alias, relationship_type in relationship_variables.items()
                if relationship_type == "HOLDS_INTEREST_IN"
            ]
            lower_bound = any(
                re.search(rf"\b{re.escape(alias)}\.valid_from\s*<=\s*\$as_of\b", masked)
                for alias in ownership_aliases
            )
            upper_bound = any(
                re.search(
                    rf"\b{re.escape(alias)}\.valid_to\s+IS\s+NULL\s+OR\s+\$as_of\s*<=\s*{re.escape(alias)}\.valid_to\b",
                    masked,
                )
                for alias in ownership_aliases
            )
            if not lower_bound:
                raise CypherGuardError("Historical ownership queries require valid_from <= $as_of")
            if not upper_bound:
                raise CypherGuardError("Historical ownership queries require inclusive valid_to")
