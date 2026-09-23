# Watheeq web console (`web/`)

A Next.js (App Router, TypeScript, Tailwind) analyst console for the existing Watheeq ownership services. It adds no backend logic. Every business value on screen comes from live FastAPI or Django responses.

## Architecture

```text
Browser ──same origin──> Next.js :3000
                           ├── pages: /  /entities/[uid]  /ask
                           └── Route Handlers (BFF, server-side only)
                                 ├── FastAPI  (FASTAPI_BASE_URL)
                                 └── Django   (DJANGO_BASE_URL)
```

Browser code only calls `/api/*` on the same origin. Backend URLs are server-side environment variables, so the backend needs no CORS changes. No `NEXT_PUBLIC_*` variables are used.

| BFF route | Backend call | Notes |
| --- | --- | --- |
| `POST /api/resolve` | FastAPI `POST /api/v1/entities/resolve` | Body forwarded as-is so FastAPI validation (422, 413) stays authoritative |
| `GET /api/entities/{uid}/ownership[?as_of=]` | FastAPI `GET /api/v1/entities/{uid}/ownership` | Current mode omits `as_of`. A malformed date gets 422 before any backend call |
| `POST /api/ask` | FastAPI `POST /api/v1/ask` | 200s timeout for local CPU inference. Relays the `X-Request-ID` header |
| `GET /api/ledger/{uid}` | Django `GET /api/v1/ledger/entities/{uid}` | Authoritative profile, filings, provenance |
| `GET /api/audit/{request_id}` | Django `GET /api/v1/audit/{request_id}` | UUID checked first. Read-only |
| `GET /api/status` | FastAPI `/ready` + Django `/ready` | Aggregated as `ready`, `degraded` or `unavailable` |
| `GET /api/health` | none | Web process liveness only (Docker healthcheck) |

Django's `POST /internal/audit` is **never** proxied.

Backend status codes and bodies are relayed unchanged. When Next.js cannot reach a backend at all, it answers 502 (unreachable) or 504 (timeout) with an `x-watheeq-bff-error` header. That lets the UI tell "backend said 503" apart from "backend is down".

## Behaviour notes

- **Entity search** shows every resolver candidate with its type (legal entity or natural person), ID, metadata, and match method. It never auto-selects, not even a single match. Multiple exact matches get an ambiguity notice. `hybrid` matches are labelled "Possible match (not exact)" because the resolver returns similarity candidates even for nonsense input.
- **Legal entity → workspace; natural person → Ask.** The backend has no person ownership or ledger endpoint (the ledger returns 404 for person IDs), so persons open Ask Watheeq with the person shown as context.
- **Current vs historical.** Current mode sends no date (the backend uses `valid_to IS NULL`). Historical mode sends one exact ISO date (the backend uses inclusive `valid_from <= as_of <= valid_to`). The mode is kept in the URL (`?as_of=`).
- **Ownership facts are shown as returned.** bps are converted to a percentage for display only (10,000 bps = 100%). Totals above or below 100% are shown with the raw bps and are not normalised or labelled invalid. Conflicts show every competing assertion side by side with dates, filings, ledger source lines, and citation IDs. No winner is picked. Cycles, including self-holdings, are flagged from the backend's `cycle` flag. No beneficial, ultimate, or control conclusions are drawn.
- **Ask outcomes** (`answered`, `abstained`, `unsupported`, `refused`, `bounded_out`, `unavailable`) are HTTP 200 data rendered as distinct states, never as exceptions. The backend's answer text is always kept: it is shown directly for answers, and under Technical details for non-answers. `[n]` markers in answers link to citation *n*. Transport and HTTP failures are a separate category (validation, 413, 502, 503, 504, malformed response).
- **Ask context** is only a canonical ID in the URL (`/ask?entity=LE-005`). The page re-confirms it with an exact resolve. The backend `/ask` contract has no entity parameter, so the question is sent exactly as written. The example chips put the selected ID into the question text, where the analyst can see and edit it.
- **Audit.** After an Ask, the request ID from `X-Request-ID` is used to fetch the Django audit record. If that fetch fails, only the audit panel shows an error and the answer stays visible. If FastAPI itself fails closed (503 "Audit persistence is unavailable"), no answer is shown. Business fields come first. Model, digest, schema, execution, and failure reason sit under a collapsed **Technical details** disclosure. Generated Cypher is only rendered after **View generated Cypher** is clicked.
- **Citations → provenance.** "View source record" loads the held entity's ledger. It finds the exactly matching ownership row (holder, entity, bps, dates, filing) and shows its source `file:line` and filing. If nothing matches exactly, it says so instead of guessing.
- **Plain language first, technical detail on request.** Each Ask status keeps its official pill (Answered, Abstained, …) plus a plain-language headline and helper. The backend's own reason text is kept word for word under a collapsed **Technical details** disclosure. HTTP errors work the same way: a plain message and **Try again**, with the raw message and HTTP status under **Technical details**.
- **"Try an example" chips** (`lib/examples.ts`) only fill the search box or question field. They never submit. They name records from the supplied seed data. The Ask examples are limited to phrasings that returned Answered with citations in 3 of 3 live runs. Phrasings the local planner repeatedly abstained on (e.g. "Who currently owns …", "Show the ownership chain for …") were left out, so a new user's first try shows the product working.
- **Untrusted text.** All registry and backend strings are rendered as React text nodes (`dir="auto"` for Arabic). There is no `dangerouslySetInnerHTML`.
- **Readiness.** The sidebar polls `/api/status` every 30s. It uses `/ready`, not `/health`, so a live FastAPI with Ollama down shows as **Degraded**.

## Design and UX approach

The first UI/UX screens were designed in Figma. They are kept as reference images in `docs/ui-reference/` (Entity Search, Entity Workspace, Ask Watheeq). Figma set the layout, hierarchy and interaction direction. The final behaviour was built by hand in this project and checked against the live backend. The reference images contain illustrative values only; none of them are used as data.

Principles:

- **Analyst first, not developer first.** Primary text is plain language, and technical detail comes second.
- **Evidence and audit are always available.** Citations, ledger provenance and the audit record are one click away from every result.
- **Conflicts are never resolved silently.** Competing records are shown side by side.
- **Ambiguous matches need the user's choice.** Nothing is auto-selected.
- **Technical detail is disclosed progressively.** Backend reasons, planner and model details, and generated Cypher sit behind collapsed **Technical details** disclosures.
- **Examples teach supported queries.** "Try an example" chips show a first-time user what they can search or ask. The Ask examples were tested live before they were included.
- **Responsive and keyboard-friendly.** Layouts work on desktop, tablet and mobile. Interactive elements have visible focus states and targets of at least 40px.

## Technology decisions

- **Next.js App Router.**
  - React UI and server-side Route Handlers live in one application.
  - Route Handlers act as the BFF between the browser and the existing backend.
  - Backend URLs and integration details stay out of browser code.
  - No backend CORS change was needed just for the UI.
  - Standalone output runs cleanly as a service in the Docker Compose stack.
- **TypeScript.** Typed API models in `types/api.ts` mirror the backend schemas. Component props are typed, and integration mistakes fail at compile time.
- **Tailwind CSS.** Handles responsive layout, spacing, typography and state styling. It keeps the frontend's dependency surface small; no component framework is used.
- **BFF instead of direct browser-to-backend calls.**

  ```text
  Browser -> Next.js /api/*        (same origin)
  Next.js -> FastAPI / Django      (server side)
  ```

  - The browser sees a single same-origin interface.
  - Timeout and transport-error translation happens in one place (`lib/backend.ts`).
  - `X-Request-ID` is relayed consistently.
  - Service URLs stay server-side.
  - The existing backend is left untouched.

  The BFF is **not** an authentication boundary today, because authentication is not implemented (see below).

## What remained unchanged

- Backend source code was not modified for the frontend.
- FastAPI and Django API contracts are unchanged.
- PostgreSQL remains authoritative. Neo4j and Weaviate remain derived, rebuildable stores.
- The backend still controls:
  - audit semantics
  - current and historical date semantics
  - `unsupported`, `refused` and `abstained` behaviour

  The frontend only displays these.

## Running

With Docker (from the repository root):

```bash
docker compose up --build -d      # includes the `web` service
open http://localhost:3000
```

The `web` service has no `depends_on` and no `env_file`. It starts even when the backend is down and shows unavailable states. It only receives `FASTAPI_BASE_URL=http://fastapi:8000` and `DJANGO_BASE_URL=http://django:8000`.

Without Docker (backend already running on the host ports):

```bash
cd web
npm ci
FASTAPI_BASE_URL=http://localhost:8001 DJANGO_BASE_URL=http://localhost:8000 npm run dev
```

Those localhost values are also the defaults when the variables are unset.

## Checks and verification

```bash
npm run lint        # ESLint (next/core-web-vitals + TypeScript)
npm run typecheck   # tsc --noEmit
npm test            # Vitest + Testing Library (jsdom), no network
npm run build       # production build (standalone output)
```

The tests cover the risky behaviours:
- ambiguity is never auto-selected
- persons never link to the workspace
- each Ask outcome state
- backend reasons sit behind collapsed technical details
- conflict rendering
- inert rendering of adversarial text
- Cypher hidden by default
- an audit failure keeps the answer
- the fail-closed 503
- `as_of` is omitted for current ownership
- `X-Request-ID` relay
- BFF transport-error labelling
- example chips fill fields without submitting and work from the keyboard

Current state:

- ESLint: passing.
- TypeScript typecheck: passing.
- Vitest + Testing Library: 29/29 passing.
- Production build: passing.
- Docker `web` container: healthy.
- Manual responsive checks at about 390px, 820px and desktop widths: no horizontal overflow seen on the Search, Ask and Ownership pages.

The final Ask example chips were chosen only from questions that returned `answered` with citations in 3 of 3 live runs:

- Who holds interests in LE-005?
- Who holds an interest in LE-001?
- Who holds interests in LE-010?
- Which entities does NP-001 hold interests in?

When an entity or person is selected, the first chip uses the same wording with the selected ID. Those substitutions were not live-tested for every possible entity.

## Authentication and JWT — future production hardening (NOT IMPLEMENTED)

Authentication and authorization are **not implemented**. There is no login, session, JWT or role handling in the frontend or the BFF.

Why it was deferred:

- The current backend defines no login, token, user or role contract.
- The assignment focused on live ownership-analysis integration.
- Fake frontend-only authentication was deliberately avoided. It would look secure without protecting anything.

Intended future architecture:

```text
User
  -> Login / Identity Provider
  -> authenticated server-side session
  -> Next.js BFF
       -> Authorization: Bearer <access token>
       -> FastAPI / Django
            -> validate token
            -> enforce user/role permissions
```

Preferred approach:

1. Add a real identity source, either an OIDC provider or a backend login flow.
2. Issue or obtain a short-lived access token (JWT).
3. Keep browser session material in secure, HttpOnly, SameSite cookies where practical, not in `localStorage`.
4. Have the Next.js Route Handlers read the authenticated session and attach the bearer token to backend calls.
5. Have FastAPI and Django each independently validate the token's signature, issuer, audience and expiry, plus the required roles or scopes.
6. Protect the audit, ledger and ownership endpoints with server-side authorization.
7. Add logout and session expiry, refresh-token handling if used, key rotation, HTTPS-only cookies, CSRF protection where applicable, and security tests.

JWT is a token format, not authorization by itself. Real protection must be enforced by FastAPI and Django on every protected request. A token held in the frontend without backend verification would not secure Watheeq.

## Known limitations

- `/ask` runs on local CPU inference and typically takes 1–3 minutes. The UI shows an elapsed timer. There is no streaming or cancellation.
- `bounded_out` has a dedicated state and a unit test. It was not triggered live, because doing so would mean changing backend bounds.
- The backend `/ask` has no structured entity parameter, so the selected context is carried only in the question text.
- Direct holders show names only when the backend includes the holder in `upstream_paths` nodes. Otherwise the canonical ID is shown.
- The local planner can still abstain on valid ownership wording (for example "Who currently owns …" or "Show the ownership chain for …"). The UI shows the abstention; it does not rephrase or retry.
- Authentication, authorization and JWT handling are not implemented yet (see above). All BFF routes are open, like the backend they front.
- No Content-Security-Policy header yet. Basic `nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy` are set.
