import os
from collections import Counter

from neo4j import GraphDatabase

from registry.models import LegalEntity, NaturalPerson, OwnershipInterest


# Compares the derived ownership graph with authoritative PostgreSQL records.
def reconcile_projection():
    expected_entity_uids = list(
        LegalEntity.objects.order_by("entity_uid").values_list(
            "entity_uid",
            flat=True,
        )
    )
    expected_person_uids = list(
        NaturalPerson.objects.order_by("person_uid").values_list(
            "person_uid",
            flat=True,
        )
    )
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
            actual_entity_uids = [
                record["entity_uid"]
                for record in session.run(
                    """
                    MATCH (entity:LegalEntity)
                    RETURN entity.entity_uid AS entity_uid
                    ORDER BY entity_uid
                    """
                )
            ]
            actual_person_uids = [
                record["person_uid"]
                for record in session.run(
                    """
                    MATCH (person:NaturalPerson)
                    RETURN person.person_uid AS person_uid
                    ORDER BY person_uid
                    """
                )
            ]
            actual_ownership = _actual_ownership_relationships(session)

    entity_result = _identity_result(
        expected_entity_uids,
        actual_entity_uids,
    )
    person_result = _identity_result(
        expected_person_uids,
        actual_person_uids,
    )
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


# Reports missing and extra ownership facts while preserving duplicates.
def _ownership_result(expected, actual):
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
