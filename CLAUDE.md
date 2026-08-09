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