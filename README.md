# Attaché

An AI chief-of-staff dashboard for people with position-heavy inboxes — first
user: a city council member.

Attaché connects to an Outlook mailbox and uses LLMs to triage, summarize, and
categorize incoming email, then drafts replies grounded in the user's stored
policy positions, matched to their writing style, and checked for contradictions
against what they've said before. Every draft cites the policies it drew from.

> **Status:** in development. Milestone 1 of 7 (skeleton + auth).
> Not yet runnable end to end.

## Why it's interesting

- **RAG over policy positions** — pgvector similarity search grounds every draft
  in the user's actual stated positions, with citations back to them.
- **A hand-written agent loop** — no LangChain. The tool-use loop in
  `services/draft_agent.py` is written from scratch, with a turn cap and a full
  trace of every call persisted for inspection.
- **Structured outputs** — triage is one schema-forced LLM call per email,
  validated with Pydantic, with a retry-on-validation-error path.
- **Evals as a first-class milestone** — labeled fixtures committed before the
  first prompt, so prompt changes are measured rather than guessed at.
- **Real multi-tenancy** — every row is scoped to a user, enforced at three
  layers: JWT-derived identity, repository signatures, and agent tools.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Frontend | Next.js (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query |
| Database | Postgres 16 + pgvector (Docker) |
| AI | Claude API (structured outputs + tool use), embeddings API |
| Integrations | Microsoft Graph via MSAL (delegated OAuth2) |

Strict layering throughout: `routers → services → repositories`, with all SQL
confined to the repository layer.

## Running locally

Requires Docker and Python 3.12.

```bash
# 1. Start Postgres (with the pgvector extension)
docker compose up -d

# 2. Configure the backend
cd backend
cp .env.example .env        # then fill in real values

# 3. Install dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows; use source .venv/bin/activate elsewhere
pip install -e ".[dev]"

# 4. Create the database schema
alembic upgrade head
```

The API server, frontend, and seed data arrive in later milestones.

## Documentation

- [`docs/ATTACHE_DESIGN.md`](docs/ATTACHE_DESIGN.md) — full design doc: requirements,
  architecture, data model, AI design, milestones.
- [`docs/progress.md`](docs/progress.md) — current build status.
- [`docs/decisions.md`](docs/decisions.md) — log of design changes and why.
