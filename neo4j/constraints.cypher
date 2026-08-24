CREATE CONSTRAINT legal_entity_entity_uid IF NOT EXISTS
FOR (entity:LegalEntity) REQUIRE entity.entity_uid IS UNIQUE;

CREATE CONSTRAINT natural_person_person_uid IF NOT EXISTS
FOR (person:NaturalPerson) REQUIRE person.person_uid IS UNIQUE;
