# Start here

1. Read `Watheeq_Osama_Take_Home_Assessment.docx` or `ASSIGNMENT.md`. They are the same document.
2. Run `python scripts/verify_pack.py` and commit the output as `PACK_VERIFICATION.json`.
3. Read `reference/graph_schema_registry.json` before you write any Cypher. It is the authority on
   the queryable surface, not the database.
4. Everything in `data/graph_seed/` is synthetic material produced by Watheeq for this assessment.
   No entity, person or asset in it is real.
5. Note the architecture before you start: Django and PostgreSQL are the system of record, Neo4j is
   a rebuildable projection, FastAPI serves the query path. Deciding this late will cost you hours.
6. Pull your local model early. A cold `docker compose up` on an unfamiliar machine is part of what
   is assessed, and model download time is not something to discover on the last evening.
7. Target 12 hours, hard cap 14, over two days. You are not expected to finish everything. Prioritise, and say what you left. Deadline Thursday, 6 August 2026, 23:59 Amman time.
8. If something in the brief is wrong or cannot be satisfied as written, email Big. That is
   expected, not penalised.
