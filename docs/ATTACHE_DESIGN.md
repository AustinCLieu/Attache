# Attaché — Design Doc / SRD

**Version:** 0.4 (final pre-build — consolidated)
**Status:** Live configuration. This doc is loaded by Claude Code via CLAUDE.md every session. Design changes MUST be reflected here and logged in `docs/decisions.md`.

---

## 1. Overview

Attaché is a multi-tenant web dashboard that acts as a digital chief of staff for busy public-facing professionals (first user: a Torrance City Council member). It connects to a user's Outlook mailbox and uses LLMs to triage, summarize, categorize, and draft replies to email — grounded in the user's stored policy positions, matched to their writing style, and checked for consistency against their stated positions. Drafts are never auto-sent; a human reviews everything.

v1 is the email workspace. The architecture and data model anticipate later tabs (people directory, events/calendar) and later monetization without redesign.

### 1.1 Goals
- Reduce time spent on email triage and response drafting.
- Ground every AI draft in the user's stored policies, with citations.
- Flag inconsistencies between drafts/past emails and current stated policies.
- Support multiple users with fully isolated data and per-user Microsoft connections.
- Portfolio-grade AI engineering: RAG, structured outputs, a hand-written agentic tool-use loop, evals as a first-class milestone, OAuth, multi-tenancy.

### 1.2 Non-Goals (v1)
- Auto-sending email (copy-to-Outlook is the v1 send path).
- Events/calendar tab (v2; sidebar shows it greyed with "soon").
- People tab UI (v2 — data model ships in v1).
- Mobile app, push notifications, shared inboxes, admin roles, fine-tuning.
- Password reset emails, email verification, MFA (documented as production hardening).
- Billing (designed for in §10, built later).

### 1.3 Users
Primary: an elected official or staffer; non-technical; values trust, control, time saved. Secondary: any professional with a position-heavy inbox.

---

## 2. Functional Requirements

### FR-1 Accounts & Auth
1. Email + password signup/login; JWT sessions in httpOnly cookie.
2. Post-login, users connect Microsoft via OAuth2 (delegated; `offline_access`, `User.Read`, `Mail.Read`).
3. Refresh tokens Fernet-encrypted at rest; access tokens refreshed server-side via `msal`.
4. Identity derives only from the verified JWT — never from request parameters.

### FR-2 Email Ingestion
1. Delta sync of inbox + sent items via Microsoft Graph (5-min poll per user + manual refresh; change-notification webhooks in v1.5).
2. Stored: graph_id, thread_id, direction, sender, recipients, subject, body text, timestamps.
3. Idempotent: upsert on `(user_id, graph_id)`. Outlook-side deletions set `hidden=true`; triage data retained.

### FR-3 Triage (workflow — one structured LLM call per new inbound email)
Outputs: `summary` (1–3 sentences); `category` (existing) or null + `suggested_new_category` + rationale (created only on user approval); `urgency` in `urgent | this_week | upcoming | fyi | ignore`; `needs_response` + reason; `sender_match` (person_id or proposed new person, user approves). Pydantic-validated; one retry with the validation error appended; then `triage_status=failed` (email still visible).

### FR-4 Draft Agent (agentic loop — only when needs_response; also on-demand from UI)
1. Tools: `lookup_person`, `fetch_thread_history`, `search_policies`, `search_similar_sent_emails`, `check_consistency`.
2. Model controls the loop; 10-turn cap; full trace persisted to `agent_trace`.
3. Output: draft + cited policy ids + consistency flags.
4. Drafts versioned; user verdict (approve/edit/reject) + `final_body` recorded — this is the eval dataset.

### FR-5 Policy Store — CRUD (title, position, tags, source link); embedded on save.

### FR-6 Consistency Checker — every draft checked pre-display (flags cite policy text); batch scan of past sent mail on demand.

### FR-7 People — name, org, role, notes, linked emails; created manually or approved from triage suggestions.

### FR-8 Review UI — see §7.

### Non-Functional Requirements
- **NFR-1 Privacy:** develop only against a seeded test mailbox; real accounts only with the owner's informed consent (constituent email = PII + potential public-records exposure). Bodies go to the LLM API only; never logged elsewhere.
- **NFR-2 Security:** argon2; JWT expiry; Fernet-encrypted OAuth tokens; every query tenant-filtered; CORS locked; secrets in env only.
- **NFR-3 Cost:** <=1 LLM call/email for triage; agent only when needed; embeddings cached by text hash; all tokens logged per user (§10).
- **NFR-4 Reliability:** every pipeline step idempotent and resumable; AI failure never hides raw email; Graph client honors 429 Retry-After.

---

## 3. System Architecture

```
+--------------+  HTTPS/JSON +----------------------------------+
|   Browser    |------------>|          FastAPI backend          |
|  Next.js UI  |<------------|  routers -> services -> repos     |
|  (JWT cookie)|             +--------+---------------+---------+
+--------------+                      |               | (on-demand redraft)
                           +----------v---+       +---v---------+
                           |  Postgres 16 |       | Claude API  |
                           |  + pgvector  |       | + embeddings|
                           |  (Docker)    |       +---^---------+
                           +------^-------+           |
                                  |             +-----+---------------+
                                  +-------------| Worker (APScheduler)|
                                                | sync->triage->draft |
                                                | ->embed, per user   |
                                                +--------+------------+
                                                         |
                                                +--------v-----+
                                                | MS Graph API |
                                                +--------------+
```

### 3.1 Components
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query. Logic-free by design: renders, collects input, calls the API. Server state via TanStack Query (cache + invalidate-on-mutation); local UI state via useState. JWT in httpOnly cookie.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 (+pydantic-settings). Strict layering — routers (HTTP, auth dependency, Pydantic I/O) -> services (business + AI logic; no HTTP objects) -> repositories (all SQL; every function requires `user_id`).
- **Worker:** APScheduler in the API process (v1), `max_instances=1`. Jobs call the services layer — the same code the API calls, so graduating to a separate process or Celery later is a deployment change, not a rewrite.
- **DB:** Postgres 16 + pgvector, Docker (`pgvector/pgvector:pg16`, named volume). The DB is also the job queue: each pipeline step's SELECT defines its backlog (§5.2).
- **LLM:** Claude API (structured outputs for triage, tool use for the agent) + a separate embeddings API behind one module. No LangChain/LangGraph — the loop and retrieval are hand-written (core learning goal). README documents what frameworks would add and when to adopt.

### 3.2 Multi-tenancy
Single schema, `user_id` on every tenant-owned table. Three enforcement layers: (1) `Depends(get_current_user)` — identity from verified JWT only; (2) repositories require + apply `user_id`; (3) agent tools take `user_id`, so retrieval can never cross tenants. Stretch: Postgres RLS.

### 3.3 Microsoft Graph
Azure app registration; auth-code flow + PKCE + `state` (CSRF); `msal` for token exchange/refresh. Delta sync per folder per user (`/me/mailFolders/{inbox|sentitems}/messages/delta`); tokens in `ms_connections`; first sync = full paginated pull. One `graph_client.py` wrapper: tokens, pagination, 429.

### 3.4 Deployment path
Dev: `docker compose up -d` (DB) + `uvicorn --reload` + `npm run dev`. Ship (M7): Vercel (frontend) + Railway/Render (API + worker + Postgres) using the backend Dockerfile. AWS migration documented as future work. The Dockerfile is written in M1 and build-tested throughout so deploy week holds no surprises.

---

## 4. Data Model

### 4.1 Shape
`users` is the tenancy root; everything hangs off it. `emails` is intentionally wide (Graph fields + triage outputs read together on every inbox view). `drafts` is separate (versions; verdict lifecycle = eval data). `ms_connections` is 1:1, isolating the most sensitive data. One email -> optional category, optional person, many drafts.

### 4.2 DDL

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,             -- argon2
  display_name  TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ms_connections (
  user_id                 UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  ms_account_id           TEXT NOT NULL,
  refresh_token_encrypted BYTEA NOT NULL,  -- Fernet
  inbox_delta_token       TEXT,
  sent_delta_token        TEXT,
  connected_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE categories (
  id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name    TEXT NOT NULL,
  source  TEXT NOT NULL DEFAULT 'user',    -- 'user' | 'ai_approved'
  UNIQUE (user_id, name)
);

CREATE TABLE people (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  org        TEXT,
  role       TEXT,
  notes      TEXT,
  emails     TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE policies (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title      TEXT NOT NULL,
  position   TEXT NOT NULL,
  tags       TEXT[] NOT NULL DEFAULT '{}',
  source_url TEXT,
  embedding  vector(1024),                 -- must match embedding model dim
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE emails (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  graph_id           TEXT NOT NULL,
  thread_id          TEXT,
  direction          TEXT NOT NULL,        -- 'inbound' | 'sent'
  sender_email       TEXT,
  sender_name        TEXT,
  recipients         TEXT[],
  subject            TEXT,
  body_text          TEXT,
  received_at        TIMESTAMPTZ,
  hidden             BOOLEAN NOT NULL DEFAULT false,
  -- triage outputs (inbound)
  summary            TEXT,
  category_id        UUID REFERENCES categories(id),
  suggested_category TEXT,
  urgency            TEXT,                 -- urgent|this_week|upcoming|fyi|ignore
  needs_response     BOOLEAN,
  triage_status      TEXT NOT NULL DEFAULT 'pending',  -- pending|done|failed
  person_id          UUID REFERENCES people(id),
  -- style retrieval (sent)
  embedding          vector(1024),
  UNIQUE (user_id, graph_id)
);

CREATE TABLE drafts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email_id          UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  version           INT NOT NULL DEFAULT 1,
  body              TEXT NOT NULL,
  cited_policy_ids  UUID[] NOT NULL DEFAULT '{}',
  consistency_flags JSONB NOT NULL DEFAULT '[]',
  agent_trace       JSONB,
  status            TEXT NOT NULL DEFAULT 'pending',   -- pending|approved|edited|rejected
  final_body        TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON emails USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON policies USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON emails (user_id, direction, received_at DESC);
CREATE INDEX ON emails (user_id, triage_status);
```

All schema changes via Alembic, committed to git. §10 adds `subscriptions` and `usage_events` later.

---

## 5. Backend & Worker Design

### 5.1 Layering (strict)

```
routers/       HTTP only: routes, status codes, Depends(get_current_user),
               Pydantic request/response models
services/      sync, triage, draft agent, consistency, embeddings, graph
               client, llm client — plain functions, shared by API and worker
repositories/  the ONLY SQL in the codebase; every function takes user_id
models.py      SQLAlchemy tables       schemas.py   Pydantic (API + LLM schemas)
config.py      pydantic-settings       security.py  hashing, JWT, Fernet
worker/jobs.py APScheduler definitions calling services
```

Router pattern:
```python
@router.get("/emails", response_model=list[EmailOut])
def list_emails(urgency: str | None = None,
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return email_repo.list_for_user(db, user.id, urgency=urgency)
```

### 5.2 Worker cycle (every 5 min per connected user; also POST /sync)
1. **Delta sync** — Graph delta per folder; upsert; save tokens.
2. **Triage** — `WHERE triage_status='pending'` -> classify -> write.
3. **Draft** — `WHERE needs_response AND no draft exists` -> agent -> store draft+trace.
4. **Embed** — `WHERE direction='sent' AND embedding IS NULL` -> embed -> store.

Every step idempotent, stateful-in-the-DB: the SELECT is the backlog, so crashes resume and nothing runs twice. Per-email try/except; repeated failure -> `failed`, move on.

### 5.3 API contract

```
POST   /auth/signup                {email, password}
POST   /auth/login                 -> sets JWT cookie
GET    /auth/me
GET    /ms/connect                 -> Microsoft authorize URL (with state)
GET    /ms/callback?code&state     public; verifies state, stores tokens
DELETE /ms/connection
POST   /sync
GET    /emails?direction&category&urgency&needs_response&page
GET    /emails/{id}                email + triage + latest draft + flags
POST   /emails/{id}/draft          (re)run agent
GET    /emails/{id}/drafts         version history
PATCH  /drafts/{id}                {status, final_body?}
GET/POST/PATCH/DELETE /policies    | /people
GET/POST/DELETE       /categories
POST   /categories/approve-suggestion {email_id}
POST   /consistency/scan
GET    /metrics                    needs-reply / urgent / drafts-ready counts
```

---

## 6. AI Design

### 6.1 Four capabilities
| Capability | Type | Trigger | Cost |
|---|---|---|---|
| Triage | Workflow (1 structured call) | Every new inbound email | Cheap, always |
| Draft agent | Agent (tool-use loop) | needs_response; UI re-draft | Expensive, selective |
| Consistency check | LLM tool (retrieval + 1 call) | Inside agent; batch scan | Moderate |
| Embeddings | API call, hash-cached | Policy save; sent sync; query time | Cheap |

### 6.2 Triage
Input: subject, truncated body, sender, category list, known-people index. Output forced into the FR-3 Pydantic schema (its JSON Schema is passed to Claude). Retry-once-with-error -> failed.

### 6.3 Draft agent — the hand-written loop
```python
messages = [{"role": "user", "content": context}]
for _ in range(10):
    resp = claude.messages.create(model=MODEL, system=SYSTEM_PROMPT,
                                  tools=TOOL_SCHEMAS, messages=messages)
    messages.append({"role": "assistant", "content": resp.content})
    tool_uses = [b for b in resp.content if b.type == "tool_use"]
    if not tool_uses:
        return extract_draft(resp), trace
    results = [run_tool(t.name, t.input, user_id) for t in tool_uses]
    messages.append({"role": "user", "content": tool_results(results)})
```

| Tool | Implementation |
|---|---|
| lookup_person(email) | repository query |
| fetch_thread_history(thread_id, limit) | repository query |
| search_policies(query, k=4) | embed -> pgvector `<=>` top-k |
| search_similar_sent_emails(query, k=4) | embed -> pgvector top-k over sent |
| check_consistency(draft) | retrieve policies -> 1 structured LLM call, contradictions only |

The loop (generic) lives in `draft_agent.py`; tools (domain) in `agent_tools.py` — separation enables testing the loop against fakes. System prompt rules: search policies before asserting any position; cite policy ids; match tone/greeting/sign-off of exemplars; never invent commitments, dates, facts; if unsure, add `[note to reviewer]`. Every turn appended to `agent_trace`.

### 6.4 Style matching (RAG, no fine-tuning)
Embed the inbound email's topic -> top-k similar sent emails -> few-shot exemplars with explicit match-the-style instruction.

### 6.5 Evals (M5, run on every prompt change — commit fixtures BEFORE writing the first prompt)
- Triage: ~50 labeled emails; per-field accuracy/F1 (pytest).
- Consistency: ~15 seeded contradiction pairs; detection rate + false positives.
- Drafts: LLM-as-judge rubric (grounding, tone, addresses the ask, no invented commitments) + real approve/edit/reject rates from `drafts`.

---

## 7. UI Design

Layout (validated via mockups): **left sidebar** (Attaché mark; nav: Inbox, People, Policies, Events greyed "soon", Settings; account block at bottom with live Outlook-connection indicator) + main content.

**Inbox (home):** greeting + sync status + "Sync now"; three metric cards (needs reply / urgent / drafts ready — one aggregate query each via GET /metrics); filter chips (All, Needs reply, Urgent, Drafts ready) + category dropdown + search; email rows.

**Email row anatomy:** sender name; urgency badge (color-coded: urgent=red, this_week=amber, fyi=blue); category chip (neutral outline — the eye sorts by urgency first); timestamp; **AI summary as the main text** (replaces subject line — summaries are signal, subjects are noise); status line ("Draft ready · cites X" / "flags scheduling conflict" / "New category suggested — review"). AI suggestions render visibly provisional (dashed chips) until approved.

**Email detail:** original message always fully visible above the draft (trust requires the source); summary box; suggested reply with version + "agent used N tools" + regenerate; citation line; consistency notes as advisory warning asides (never blocking); actions: Approve / Edit / Reject + **Copy to Outlook** (the v1 send path — Attaché never sends).

**Settings:** tabbed (Categories, Policies, People, Connection). Pending AI category suggestions appear as approve/dismiss banners. Policy cards show "Cited in N drafts" (query over `drafts.cited_policy_ids`) — closes the trust loop and surfaces stale policies.

Component inventory: see §9 frontend tree. Built with shadcn/ui primitives + Tailwind.

---

## 8. Security & Privacy

- Passwords: argon2 (`argon2-cffi`); never stored/logged plaintext.
- Sessions: JWT (`python-jose`), short expiry, httpOnly cookie.
- OAuth: `msal`; `state` verified; refresh tokens Fernet-encrypted, key in env.
- Tenancy: identity from JWT only; repositories and agent tools require `user_id`; two-user isolation test covers every resource type.
- Transport: HTTPS; CORS restricted; rate limiting on auth routes.
- Data: seeded test mailbox for all development; real mailbox only with informed consent; bodies to the LLM API only.
- Production hardening (documented, not built): reset/verification emails, MFA, RLS, audit log.

---

## 9. Repository Structure (complete v1 tree; M# = milestone it appears)

```
attache/
├── CLAUDE.md                          # Claude Code context (M1) — see §11
├── README.md                          # setup, architecture, demo (M7)
├── .gitignore
├── docker-compose.yml                 # pgvector/pgvector:pg16 + volume (M1)
├── docs/
│   ├── ATTACHE_DESIGN.md              # this file — imported by CLAUDE.md
│   └── decisions.md                   # design-drift log (living)
├── backend/
│   ├── Dockerfile                     # prod image; build-tested from M1
│   ├── pyproject.toml                 # fastapi sqlalchemy alembic pydantic
│   │                                  # pydantic-settings argon2-cffi python-jose
│   │                                  # cryptography msal httpx anthropic
│   │                                  # apscheduler psycopg pgvector pytest
│   ├── .env / .env.example            # real (ignored) / dummy keys (committed)
│   ├── alembic.ini
│   ├── alembic/versions/
│   │   ├── 001_users.py                                  # M1
│   │   ├── 002_ms_connections_emails.py                  # M2
│   │   ├── 003_triage_fields.py                          # M3
│   │   └── 004_categories_people_policies_drafts.py      # M3–M5
│   ├── app/
│   │   ├── main.py                    # app factory, CORS, routers, scheduler (M1)
│   │   ├── config.py  security.py  database.py  models.py  schemas.py
│   │   ├── api/
│   │   │   ├── deps.py                # get_current_user (M1)
│   │   │   └── routers/
│   │   │       ├── auth.py            # M1
│   │   │       ├── ms.py  sync.py     # M2
│   │   │       ├── emails.py          # M2–M5
│   │   │       ├── categories.py      # M3
│   │   │       ├── people.py  policies.py               # M4
│   │   │       ├── drafts.py          # M5
│   │   │       └── consistency.py     # M6
│   │   ├── repositories/
│   │   │   ├── user_repo.py           # M1
│   │   │   ├── email_repo.py          # M2; vector search M4
│   │   │   ├── category_repo.py  person_repo.py         # M3
│   │   │   ├── policy_repo.py         # M4; vector search
│   │   │   └── draft_repo.py          # M5
│   │   ├── services/
│   │   │   ├── graph_client.py  sync_service.py         # M2
│   │   │   ├── llm_client.py  triage_service.py         # M3
│   │   │   ├── embeddings.py          # M4
│   │   │   ├── draft_agent.py  agent_tools.py           # M5
│   │   │   └── consistency_service.py # M6
│   │   └── worker/jobs.py             # M2–M5
│   ├── scripts/seed.py                # ~30 fake emails + policies (stub M1, real M3)
│   ├── tests/
│   │   ├── conftest.py                # test DB + two-user fixtures (M1)
│   │   ├── test_auth.py               # M1
│   │   ├── test_sync.py               # idempotency (M2)
│   │   ├── test_triage.py             # M3
│   │   ├── test_agent.py              # loop cap, trace, tool tenancy (M5)
│   │   └── test_isolation.py          # two users x every resource (M7, run always)
│   └── evals/
│       ├── fixtures/triage_labeled.json        # commit BEFORE first prompt
│       ├── fixtures/contradictions.json        # M6
│       ├── run_triage_eval.py  run_consistency_eval.py
│       └── judge_rubric.md
└── frontend/
    ├── package.json  next.config.ts  tailwind.config.ts  tsconfig.json
    ├── components.json                # shadcn/ui
    ├── .env.local                     # NEXT_PUBLIC_API_URL (ignored)
    ├── lib/
    │   ├── api.ts                     # fetch wrapper (M1)
    │   ├── types.ts                   # TS mirrors of Pydantic schemas
    │   └── queries.ts                 # TanStack Query hooks
    ├── components/
    │   ├── ui/                        # shadcn/ui generated
    │   ├── Sidebar.tsx  EmailList.tsx                    # M2
    │   ├── MetricCards.tsx  EmailFilters.tsx
    │   │   UrgencyBadge.tsx  CategorySuggestion.tsx      # M3
    │   ├── PolicyForm.tsx             # M4
    │   ├── DraftEditor.tsx            # M5
    │   └── ConsistencyFlag.tsx        # M6
    └── app/
        ├── layout.tsx  page.tsx  login/page.tsx          # M1
        ├── connect/page.tsx           # M2
        ├── inbox/page.tsx             # M2/M3
        ├── inbox/[id]/page.tsx        # M3/M5
        └── settings/
            ├── layout.tsx  categories/page.tsx           # M3
            ├── policies/page.tsx  people/page.tsx        # M4
            └── connection/page.tsx    # M2
```

Structural rules: no `utils/`, `helpers/`, or `managers/` folders — everything has a home in the four backend layers or three frontend folders. ~60 files total for v1.

### Environment variables
`DATABASE_URL`, `SECRET_KEY`, `FERNET_KEY`, `ANTHROPIC_API_KEY`, `EMBEDDINGS_API_KEY`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_REDIRECT_URI`, `FRONTEND_ORIGIN` — loaded once by pydantic-settings; missing values fail at startup.

---

## 10. Monetization (designed now, built later)

The architecture already provides the seams; nothing below requires redesign.

1. **Payments — Stripe** (test mode first): Checkout session -> hosted payment -> webhook `POST /stripe/webhook` updates entitlements. New table `subscriptions(user_id, stripe_customer_id, plan, status, current_period_end)` + one router. Same signed-callback pattern as the Graph OAuth flow.
2. **Metering:** `usage_events(user_id, event_type, input_tokens, output_tokens, created_at)` written from `llm_client.py` — all Claude calls already pass through it. (Interim cost guard, buildable in ~1 hour: hard per-user monthly token cap checked in `llm_client`.)
3. **Enforcement:** plan/quota check in services before triage batches and agent runs — one check covers API and worker since they share the services layer.

---

## 11. CLAUDE.md (committed at repo root, M1)

```markdown
# Attaché — AI chief-of-staff dashboard

Full design doc: @docs/ATTACHE_DESIGN.md (architecture, schema, milestones).
We build milestone by milestone (doc §13). Ask which milestone we're on
if unclear. Log design changes in docs/decisions.md AND update the doc.

## Stack
- backend/: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- frontend/: Next.js App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query
- Postgres 16 + pgvector via docker-compose; Claude API; msal for MS OAuth

## Commands
- DB: docker compose up -d        API: cd backend && uvicorn app.main:app --reload
- Frontend: cd frontend && npm run dev
- Migrations: alembic revision --autogenerate -m "..." && alembic upgrade head
- Tests: cd backend && pytest     Evals: pytest evals/

## Rules
- Strict layering: routers -> services -> repositories. SQL only in
  repositories/. Services never import FastAPI request objects.
- Every repository function takes user_id and filters by it. No exceptions.
- No LangChain/LangGraph — agent loop is hand-written in services/draft_agent.py.
- Never touch .env or print secrets. Never auto-send email — drafts only.
- Schema changes only via Alembic. New categories only via user approval flow.
- After changing any LLM prompt, run the eval suite before committing.
```

---

## 12. Development Workflow (AI-assisted)

- Claude Code sessions start fresh; CLAUDE.md (+ this doc via import) is the persistent context. **Doc drift is a bug**: design changes update this doc + `decisions.md` in the same commit.
- Work plan-first, milestone-sized: name the milestone and section ("implement FR-4 per §6.3"), review the proposed plan against this doc, then implement. Commit every working increment.
- Claude Code writes tests alongside code and runs them before "done."
- Learning-goal role inversion: the agent loop, OAuth flow, and triage schema are written by the author and reviewed by Claude Code; CRUD, layouts, and boilerplate are delegated freely. Exit criterion: able to explain every line of `draft_agent.py` in an interview.
- Two-user rule: from M1 on, every feature is manually tested with two accounts.

---

## 13. Milestones

### M1 — Skeleton + auth
Compose file; Alembic baseline (`users`); config/security/database modules; signup/login/JWT + `/auth/me`; Next.js shell + login + api client; CLAUDE.md + this doc in docs/; backend Dockerfile (build-tested); seed stub; conftest with two-user fixture.
**Done when:** two users can sign up, log in, and see their own `/auth/me`.

### M2 — Outlook connect + sync
Azure registration; msal connect/callback with state; `ms_connections` + `emails` migrations; graph_client (tokens, pagination, 429); delta sync + upsert; scheduler job + POST /sync; Sidebar + plain inbox list; connection settings page.
**Done when:** test mailbox appears in UI; re-sync duplicates nothing; Outlook deletion hides the row.

### M3 — Triage
Triage schema + prompt; llm_client (schema-forced call, retry, token logging); worker step 2; metric cards; badges/chips/filters; category- and person-suggestion approval flows; real seed script.
**Done when:** seeded emails classified within one cycle; filters work; an approved suggested category is used thereafter.

### M4 — Reference data + retrieval
Policies/people/categories CRUD + settings pages; embeddings module (hash cache); embed-on-save; worker step 4; both vector-search functions verified against known-similar seed data.
**Done when:** `search_policies('road repair')` returns the infrastructure policy first.

### M5 — Draft agent + evals
Tool schemas + implementations; the loop (10-turn cap, trace); system prompt; worker step 3 + POST /emails/{id}/draft; DraftEditor UI (citations, verdicts, versions); eval fixtures + triage runner; first eval-driven prompt iteration.
**Done when:** a seeded-topic email yields a draft citing the right policy; trace shows the calls; triage eval reports a baseline.

### M6 — Consistency
check_consistency wired into agent; ConsistencyFlag UI; batch scan endpoint + results view; consistency eval set.
**Done when:** a seeded contradicting draft is flagged with the policy text.

### M7 — Hardening + ship
Isolation test across all resources; failure-path tests; seed polish; README (diagrams, eval results, run instructions); demo video; deploy (Vercel + Railway/Render); future-work section (AWS, webhooks, Mail.Send, billing).
**Done when:** a stranger can clone, seed, run, and understand it in 15 minutes.

---

## 14. Risks & Open Questions

- Azure app registration friction — buffer in M2; use a Microsoft 365 dev tenant.
- Long threads vs context — truncate for triage; agent pulls history on demand.
- Embedding model chosen in M4 and locked (dimension in schema; change = re-embed).
- Open: Mail.Send (deferred; copy-to-Outlook is v1) · Graph webhooks (v1.5; needs public callback URL) · Stripe live mode (test mode only until real users).

---

## 15. Change Log

- v0.4 — consolidated: full repo tree (§9), UI design from mockups (§7), monetization plan (§10), CLAUDE.md (§11), AI-assisted workflow (§12), /metrics endpoint, decisions.md introduced.
- v0.3 — implementation depth: layering, worker idempotency, agent pseudocode, auth flows, build order. Renamed to Attaché.
- v0.2 — multi-tenancy, self-hosted Postgres, initial SRD.