## Architecture Rules

### PostgreSQL and Django

* PostgreSQL is the planned system of record.
* Django owns PostgreSQL writes and audit persistence.
* Django project configuration stays under `django_service/watheeq/`.
* Domain functionality stays under `django_service/registry/`.
* Data-loading and graph-projection commands belong under:

  `django_service/registry/management/commands/`

### FastAPI

* FastAPI orchestrates the planned query pipeline.
* Keep `main.py` small.
* Request and response contracts belong in `schemas.py`.
* External service connections belong under `app/clients/`.
* Query orchestration belongs in `pipeline.py`.
* Deterministic Cypher validation belongs in `guards.py`.

### Neo4j

* Neo4j is a rebuildable graph projection, not the system of record.
* Application queries must be read-only.
* Do not add write-capable query behavior to the FastAPI request path.
* Generated Cypher must never execute without deterministic validation.

### Weaviate

* Weaviate is used only for vector storage and vector search.
* Built-in Weaviate vectorizers must remain disabled.
* Embeddings will be generated explicitly by local Python code.
* Do not enable hosted embedding providers.

### Ollama

* Ollama must remain local.
* The configured model is `qwen3:4b`.
* Do not add hosted model APIs.
* Do not use the model digest as the runtime model name.
* Model output must be treated as untrusted generated code or text.

## Docker Rules

* Preserve the existing Docker Compose service names unless explicitly instructed.
* Internal connections must use Docker service names, not `localhost`.
* Do not remove persistent named volumes.
* Do not run `docker compose down -v` unless explicitly requested.
* Do not add frontend or monitoring containers unless explicitly requested.
* Healthchecks must test process availability.
* Readiness checks may test required dependencies.

## Code Quality

* Use Python 3.11-compatible code.
* Prefer clear functions with one responsibility.
* Use type hints where they improve clarity.
* Add comments only when the reason is not obvious.
* Avoid duplicated configuration.
* Avoid premature repository, manager, factory, or plugin abstractions.
* Handle failures explicitly.
* Do not swallow exceptions silently.
* Do not claim success when a command or test fails.

## Testing and Verification

After relevant changes, run the smallest applicable checks.

Common checks include:

```bash
python -m compileall django_service fastapi_service
docker compose exec -T django python manage.py check
docker compose config
docker compose ps
git diff --check
git status --short
```

For Docker or connectivity changes, also verify:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8001/ready
```

Report the real output of checks. Do not invent passing results.

## Git Rules

* Do not commit automatically.
* Do not push automatically.
* Do not rewrite Git history.
* Do not modify unrelated files.
* Show `git status --short` after completing a task.
* Propose one clear commit message.
* Keep each change focused on one logical purpose.

## Documentation Rules

* Keep `README.md` consistent with the actual implementation.
* Clearly separate completed, planned, and excluded work.
* Do not remove recorded limitations.
* Do not invent evaluation results, metrics, tests, or implementation progress.
* Update `AI_USE.md` honestly when AI-assisted implementation changes materially.

## Final Response

After completing a task, report:

1. Files changed.
2. What was implemented.
3. What was intentionally not implemented.
4. Verification commands and actual results.
5. Any unresolved problem.
6. `git status --short`.
7. A proposed commit message.