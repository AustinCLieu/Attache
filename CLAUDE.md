# Attaché — AI chief-of-staff dashboard

Full design doc: @docs/ATTACHE_DESIGN.md (architecture, schema, milestones).
Current progress: @docs/progress.md — the session state file: current
milestone, done / in-progress / next action, gotchas. Read it at the start of
each session; whenever you commit, update it in the same commit.
We build milestone by milestone (doc §13). Ask which milestone we're on
if unclear. Log design changes in docs/decisions.md AND update the doc.

## Stack
- backend/: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- frontend/: Next.js App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query
- Postgres 16 + pgvector via docker-compose (RDS in prod); Anthropic API;
  msal for MS OAuth
- Production (M8): AWS — App Runner, RDS, ECR, Secrets Manager, IAM, CloudWatch

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
- All config via BaseSettings/env — no hardcoded URLs, hosts, or credentials
  (this is what makes the AWS deployment a zero-code-change migration).

## Working style
- After giving code, config, or a command, explain each part — what it does
  and why — as a beginner-friendly walkthrough. The author is learning; teach,
  don't just deliver. Flag typos/mistakes in the author's files when reviewing.
- Before/after running any command, explain what it does, why we're running it,
  and what each part means (flags, paths, sub-commands). Assume the author is
  learning the tooling, not just the code.
- Length: answer clarifying questions in a few short paragraphs — enough to
  actually teach, but not an essay. Save the long walkthroughs for new parts
  (new file, new tool, new concept). Don't pad with tangents the author didn't
  ask about; if there's more worth knowing, offer it in a line and let them ask.
- Claude writes the code; the author reviews it to learn. Write the files,
  then walk through what you did and why, assuming no prior knowledge. Every
  code delivery includes: what the code does and how it works, why it was
  built that way (and what the alternatives were), and a list of every
  tool/package/keyword introduced — what it is, what it does for us, and why
  it was chosen. Point out anything the author should look at closely.
- Always track commit points. After each working increment, say explicitly
  whether it is time to commit, which files to stage, and the message to use
  (one logical concern per commit; the repo must be left in a working state).
  Never let uncommitted work pile up silently.
- The review is the learning, so optimize for readability over cleverness:
  no dense one-liners where three plain ones read better. Design doc §12
  exit criterion still holds — the author must be able to explain every line
  of `draft_agent.py`, so slow down and go deeper on the agent loop, the
  OAuth flow, and the triage schema.
