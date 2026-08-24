import os

from neo4j import GraphDatabase

from registry.models import LegalEntity, NaturalPerson, OwnershipInterest


LEGAL_ENTITY_CONSTRAINT = """
CREATE CONSTRAINT legal_entity_entity_uid IF NOT EXISTS
FOR (entity:LegalEntity) REQUIRE entity.entity_uid IS UNIQUE
"""

NATURAL_PERSON_CONSTRAINT = """
CREATE CONSTRAINT natural_person_person_uid IF NOT EXISTS
FOR (person:NaturalPerson) REQUIRE person.person_uid IS UNIQUE
"""


# Rebuilds the ownership graph from the authoritative PostgreSQL records.
def project_graph():
    driver = GraphDatabase.driver(
        os.environ["GRAPH_DB_URI"],
        auth=(
            os.environ["GRAPH_DB_USER"],
            os.environ["GRAPH_DB_PASSWORD"],
        ),
    )

    with driver:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            session.run(LEGAL_ENTITY_CONSTRAINT)
            session.run(NATURAL_PERSON_CONSTRAINT)

            legal_entity_count = _project_legal_entities(session)
            natural_person_count = _project_natural_persons(session)
            ownership_interest_count = _project_ownership_interests(session)

    return {
        "LegalEntity": legal_entity_count,
        "NaturalPerson": natural_person_count,
        "HOLDS_INTEREST_IN": ownership_interest_count,
    }


# Creates LegalEntity nodes with only schema-supported properties.
def _project_legal_entities(session):
    count = 0

    for entity in LegalEntity.objects.all():
        session.run(
            """
            CREATE (entity:LegalEntity {
                entity_uid: $entity_uid,
                legal_name: $legal_name,
                legal_name_ar: $legal_name_ar,
                jurisdiction: $jurisdiction,
                registration_no: $registration_no,
                incorporation_date: $incorporation_date,
                status: $status,
                status_as_of: $status_as_of
            })
            """,
            entity_uid=entity.entity_uid,
            legal_name=entity.legal_name,
            legal_name_ar=entity.legal_name_ar,
            jurisdiction=entity.jurisdiction,
            registration_no=entity.registration_no,
            incorporation_date=entity.incorporation_date,
            status=entity.status,
            status_as_of=entity.status_as_of,
        )
        count += 1

    return count


# Creates NaturalPerson nodes with only schema-supported properties.
def _project_natural_persons(session):
    count = 0

    for person in NaturalPerson.objects.all():
        session.run(
            """
            CREATE (person:NaturalPerson {
                person_uid: $person_uid,
                full_name: $full_name,
                full_name_ar: $full_name_ar,
                nationality: $nationality,
                dob_year: $dob_year
            })
            """,
            person_uid=person.person_uid,
            full_name=person.full_name,
            full_name_ar=person.full_name_ar,
            nationality=person.nationality,
            dob_year=person.dob_year,
        )
        count += 1

    return count


# Creates person or entity ownership relationships from validated ORM rows.
def _project_ownership_interests(session):
    count = 0

    for interest in OwnershipInterest.objects.all():
        relationship_properties = {
            "bps": interest.bps,
            "valid_from": interest.valid_from,
            "valid_to": interest.valid_to,
            "filing_uid": interest.filing_id,
        }

        if interest.holder_person_id:
            session.run(
                """
                MATCH (holder:NaturalPerson {person_uid: $holder_uid})
                MATCH (held:LegalEntity {entity_uid: $held_uid})
                CREATE (holder)-[:HOLDS_INTEREST_IN {
                    bps: $bps,
                    valid_from: $valid_from,
                    valid_to: $valid_to,
                    filing_uid: $filing_uid
                }]->(held)
                """,
                holder_uid=interest.holder_person_id,
                held_uid=interest.held_entity_id,
                **relationship_properties,
            )
        else:
            session.run(
                """
                MATCH (holder:LegalEntity {entity_uid: $holder_uid})
                MATCH (held:LegalEntity {entity_uid: $held_uid})
                CREATE (holder)-[:HOLDS_INTEREST_IN {
                    bps: $bps,
                    valid_from: $valid_from,
                    valid_to: $valid_to,
                    filing_uid: $filing_uid
                }]->(held)
                """,
                holder_uid=interest.holder_entity_id,
                held_uid=interest.held_entity_id,
                **relationship_properties,
            )

        count += 1

    return count
