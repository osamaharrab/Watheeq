"""Compare the rebuildable Neo4j ownership projection with PostgreSQL truth."""
import os
from collections import Counter

from neo4j import GraphDatabase

from registry.models import LegalEntity, NaturalPerson, OwnershipInterest


# Compares the derived ownership graph with authoritative PostgreSQL records.
def reconcile_projection():
    # Compare projected nodes and ownership edges independently before deciding success.
    expected_entities = _expected_legal_entities()
    expected_persons = _expected_natural_persons()
    expected_ownership = _expected_ownership_relationships()

    driver = GraphDatabase.driver(
        os.environ["GRAPH_DB_URI"],
        auth=(
            os.environ["GRAPH_DB_USER"],
            os.environ["GRAPH_DB_PASSWORD"],
        ),
    )

    with driver:
        with driver.session() as session:
            actual_entities = _actual_legal_entities(session)
            actual_persons = _actual_natural_persons(session)
            actual_ownership = _actual_ownership_relationships(session)

    entity_result = _node_result(expected_entities, actual_entities, "entity_uid")
    person_result = _node_result(expected_persons, actual_persons, "person_uid")
    ownership_result = _ownership_result(
        expected_ownership,
        actual_ownership,
    )

    return {
        "reconciled": (
            entity_result["matches"]
            and person_result["matches"]
            and ownership_result["matches"]
        ),
        "LegalEntity": entity_result,
        "NaturalPerson": person_result,
        "HOLDS_INTEREST_IN": ownership_result,
    }


def _expected_legal_entities():
    """Read every LegalEntity property written by the graph projection."""
    return [
        {
            "entity_uid": entity.entity_uid,
            "legal_name": entity.legal_name,
            "legal_name_ar": entity.legal_name_ar,
            "jurisdiction": entity.jurisdiction,
            "registration_no": entity.registration_no,
            "incorporation_date": _comparison_value(entity.incorporation_date),
            "status": entity.status,
            "status_as_of": _comparison_value(entity.status_as_of),
        }
        for entity in LegalEntity.objects.order_by("entity_uid")
    ]


def _expected_natural_persons():
    """Read every NaturalPerson property written by the graph projection."""
    return [
        {
            "person_uid": person.person_uid,
            "full_name": person.full_name,
            "full_name_ar": person.full_name_ar,
            "nationality": person.nationality,
            "dob_year": person.dob_year,
        }
        for person in NaturalPerson.objects.order_by("person_uid")
    ]


def _actual_legal_entities(session):
    """Read the LegalEntity projection in the same shape as PostgreSQL expectations."""
    return [
        dict(record)
        for record in session.run(
            """
            MATCH (entity:LegalEntity)
            RETURN entity.entity_uid AS entity_uid,
                   entity.legal_name AS legal_name,
                   entity.legal_name_ar AS legal_name_ar,
                   entity.jurisdiction AS jurisdiction,
                   entity.registration_no AS registration_no,
                   toString(entity.incorporation_date) AS incorporation_date,
                   entity.status AS status,
                   toString(entity.status_as_of) AS status_as_of
            ORDER BY entity_uid
            """
        )
    ]


def _actual_natural_persons(session):
    """Read the NaturalPerson projection in the same shape as PostgreSQL expectations."""
    return [
        dict(record)
        for record in session.run(
            """
            MATCH (person:NaturalPerson)
            RETURN person.person_uid AS person_uid,
                   person.full_name AS full_name,
                   person.full_name_ar AS full_name_ar,
                   person.nationality AS nationality,
                   person.dob_year AS dob_year
            ORDER BY person_uid
            """
        )
    ]


def _comparison_value(value):
    # PostgreSQL dates and Neo4j dates compare reliably after ISO normalization.
    return value.isoformat() if hasattr(value, "isoformat") else value


# Builds the ownership facts expected from PostgreSQL using stable string dates.
def _expected_ownership_relationships():
    relationships = []

    for interest in OwnershipInterest.objects.order_by("pk"):
        if interest.holder_person_id:
            holder_type = "NaturalPerson"
            holder_uid = interest.holder_person_id
        else:
            holder_type = "LegalEntity"
            holder_uid = interest.holder_entity_id

        valid_to = None
        if interest.valid_to is not None:
            valid_to = interest.valid_to.isoformat()

        relationships.append(
            (
                holder_type,
                holder_uid,
                interest.held_entity_id,
                interest.bps,
                interest.valid_from.isoformat(),
                valid_to,
                interest.filing_id,
            )
        )

    return relationships


# Reads the projected ownership facts without changing the graph.
def _actual_ownership_relationships(session):
    records = session.run(
        """
        MATCH (holder)-[interest:HOLDS_INTEREST_IN]->(held)
        RETURN
            CASE
                WHEN holder:NaturalPerson THEN 'NaturalPerson'
                WHEN holder:LegalEntity THEN 'LegalEntity'
                ELSE 'Unexpected'
            END AS holder_type,
            CASE
                WHEN holder:NaturalPerson THEN holder.person_uid
                WHEN holder:LegalEntity THEN holder.entity_uid
                ELSE null
            END AS holder_uid,
            held.entity_uid AS held_uid,
            interest.bps AS bps,
            toString(interest.valid_from) AS valid_from,
            toString(interest.valid_to) AS valid_to,
            interest.filing_uid AS filing_uid
        """
    )

    relationships = []
    for record in records:
        relationships.append(
            (
                record["holder_type"],
                record["holder_uid"],
                record["held_uid"],
                record["bps"],
                record["valid_from"],
                record["valid_to"],
                record["filing_uid"],
            )
        )

    return relationships


# Reports missing and extra node identities, including accidental duplicates.
def _identity_result(expected, actual):
    """Report missing or extra projected identities, including duplicate rows."""
    expected_counts = Counter(expected)
    actual_counts = Counter(actual)
    result = {
        "expected": len(expected),
        "actual": len(actual),
        "matches": expected_counts == actual_counts,
    }

    if not result["matches"]:
        result["missing_uids"] = sorted(
            (expected_counts - actual_counts).elements()
        )
        result["extra_uids"] = sorted(
            (actual_counts - expected_counts).elements()
        )

    return result


def _node_result(expected, actual, uid_key):
    """Report identity mismatches first, then projected-property drift by UID."""
    result = _identity_result(
        [node[uid_key] for node in expected],
        [node[uid_key] for node in actual],
    )
    if not result["matches"]:
        return result

    expected_by_uid = {node[uid_key]: node for node in expected}
    actual_by_uid = {node[uid_key]: node for node in actual}
    mismatches = [
        uid
        for uid in sorted(expected_by_uid)
        if expected_by_uid[uid] != actual_by_uid[uid]
    ]
    if mismatches:
        result["matches"] = False
        result["property_mismatches"] = mismatches
    return result


# Reports missing and extra ownership facts while preserving duplicates.
def _ownership_result(expected, actual):
    # Counter comparison preserves duplicate assertions, including same-day conflicts.
    expected_counts = Counter(expected)
    actual_counts = Counter(actual)
    result = {
        "expected": len(expected),
        "actual": len(actual),
        "matches": expected_counts == actual_counts,
    }

    if not result["matches"]:
        result["missing_relationships"] = list(
            (expected_counts - actual_counts).elements()
        )
        result["extra_relationships"] = list(
            (actual_counts - expected_counts).elements()
        )

    return result
