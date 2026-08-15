# Build Progress

Living tracker of where we are in the build. Loaded into Claude Code each
session via CLAUDE.md. Update this as parts complete; commit it with the work.
Git history = what's done; this file = the plan, the phase breakdown, and the
next action.

**Current position:** Milestone 1 → Phase B → `app/schemas.py` next.
Parts 1–2 of Phase B done (`users` model + Alembic baseline applied; DB at
revision `001`).

---

## Milestone 1 — Skeleton + auth

Exit criterion (design doc §13): two users can sign up, log in, and each see
their own `/auth/me`.

We break each milestone into small phases and each phase into parts, going
through them one at a time so the author can learn (see CLAUDE.md Working style).

### Phase A — Infra & config
- [x] Part 1 — `docker-compose.yml` (Postgres 16 + pgvector, named volume, healthcheck) — commit `8a18073`
- [x] Part 2 — `.gitignore` — commit `8a18073`
- [x] Part 3 — `backend/pyproject.toml` + `.venv` (deps installed) — commit `8a18073`
- [x] Part 4 — `backend/.env.example` (committed) + `.env` (git-ignored, real keys generated) — commit `8a18073`
- [x] Part 5 — `app/config.py` (pydantic-settings; loads & validates `.env`, fails fast) — verified
- [x] Part 6 — `app/database.py` (SQLAlchemy 2.0 engine, SessionLocal, Base, `get_db`) — verified (SELECT 1 OK)
- [x] Part 7 — `app/security.py` (argon2 hashing, JWT create/verify, Fernet helpers) — verified
- Parts 5–7 → second commit (`feat: backend foundation modules`)

### Phase B — Data + auth (backend)
- [x] `app/models.py` — `users` table (tenancy root)
- [x] Alembic baseline + `001_users.py` migration — `alembic upgrade head` applied
- [ ] `app/schemas.py` — Pydantic I/O (signup, login, user out)
- [ ] `repositories/user_repo.py` — the only SQL for users
- [ ] `api/deps.py` — `get_current_user` (identity from JWT only)
- [ ] `api/routers/auth.py` — signup / login (sets JWT cookie) / me
- [ ] `app/main.py` — app factory, CORS, router registration
- First milestone where the app actually does something.

### Phase C — Tests & Docker
- [ ] `tests/conftest.py` — test DB + two-user fixtures
- [ ] `tests/test_auth.py` — signup, login, wrong password, me-returns-own, isolation
- [ ] `scripts/seed.py` — stub (becomes real in M3)
- [ ] `backend/Dockerfile` — build-tested

### Phase D — Frontend shell
- [ ] Next.js + TS + Tailwind + shadcn init, `components.json`, `.env.local`
- [ ] `lib/api.ts`, `lib/types.ts`, `lib/queries.ts`
- [ ] `app/layout.tsx`, `app/page.tsx`, `app/login/page.tsx`

### Phase E — Verify
- [ ] pytest green
- [ ] Docker image builds
- [ ] Two-account manual walkthrough (the M1 exit criterion)

---

## Resume checklist (start of each session)
1. `docker compose start` — bring the DB back up.
2. Read this file to see the next unchecked part.
3. Continue from there.

## Key decisions so far
- Dev runs Option 1: Postgres in Docker, API in local `.venv` via `uvicorn --reload`.
  Dockerfile still written/build-tested (Phase C) for M7 deploy.
- Commit granularity: one logical concern per commit (infra vs. docs kept separate).
