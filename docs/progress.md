# Build Progress

Living tracker of where the build stands. Loaded into Claude Code each session
via CLAUDE.md, and updated in the same commit as the work it describes.
Git history records what shipped; this file records the plan, the current
position, and the next action.

**Current position:** M1 (Skeleton + auth) → Phase D (frontend shell) next.
Phases A–C complete: 16 auth tests green, Docker image build-tested and
verified to boot as a non-root user.

Milestones and their exit criteria are defined in `ATTACHE_DESIGN.md` §13.
Each is broken into phases, and each phase into parts, worked one at a time.

---

## M1 — Skeleton + auth

**Exit criterion:** two users can sign up, log in, and each see their own
`/auth/me`.

### Phase A — Infra & config
- [x] `docker-compose.yml` — Postgres 16 + pgvector, named volume, healthcheck
- [x] `.gitignore`
- [x] `backend/pyproject.toml` + `.venv`
- [x] `.env.example` (committed) + `.env` (git-ignored)
- [x] `app/config.py` — pydantic-settings; validates env, fails fast
- [x] `app/database.py` — SQLAlchemy 2.0 engine, SessionLocal, Base, `get_db`
- [x] `app/security.py` — argon2 hashing, JWT create/verify, Fernet helpers

### Phase B — Data + auth
- [x] `app/models.py` — `users` table (tenancy root)
- [x] Alembic baseline + `001_users.py`, applied
- [x] `app/schemas.py` — signup / login / user-out
- [x] `repositories/user_repo.py` — get_by_id / get_by_email / create
- [x] `api/deps.py` — `get_current_user`, identity from verified JWT only
- [x] `api/routers/auth.py` — signup / login (sets JWT cookie) / logout / me
- [x] `app/main.py` — app factory, CORS, router registration, `/health`

### Phase C — Tests & container
- [x] `tests/conftest.py` — `attache_test` DB, rollback-per-test, two-user fixtures
- [x] `tests/test_auth.py` — 16 tests: signup, login, forged token, isolation
- [x] `scripts/seed.py` — stub, idempotent (becomes real in M3)
- [x] `backend/Dockerfile` — build-tested; runs non-root, no `--reload`

### Phase D — Frontend shell
- [ ] Next.js + TS + Tailwind + shadcn init, `components.json`, `.env.local`
- [ ] `lib/api.ts`, `lib/types.ts`, `lib/queries.ts`
- [ ] `app/layout.tsx`, `app/page.tsx`, `app/login/page.tsx`

### Phase E — Verify
- [ ] pytest green · Docker image builds · two-account walkthrough

**External dependencies to start now** (they block on third parties, not on us):
Microsoft 365 dev tenant + Azure app registration (§14 risk); AWS account with
the $10 Budget alert set on creation; confirm `pgvector` availability on the
target RDS Postgres version (§14 lists this as unverified).

---

## M2 — Outlook connect + sync

**Exit criterion:** the test mailbox appears in the UI; re-sync duplicates
nothing; an Outlook-side deletion hides the row.

- [ ] Migration `002_ms_connections_emails.py`
- [ ] `services/graph_client.py` — token refresh, pagination, 429 Retry-After
- [ ] `api/routers/ms.py` — auth-code + PKCE + `state`; Fernet-encrypted tokens
- [ ] `services/sync_service.py` — delta sync per folder, upsert on
      `(user_id, graph_id)`
- [ ] `POST /sync` + `worker/jobs.py` (APScheduler, `max_instances=1`)
- [ ] `Sidebar.tsx`, `EmailList.tsx`, connection settings page

---

## M3 — Triage

**Exit criterion:** seeded emails are classified within one worker cycle;
filters work; an approved suggested category is used thereafter.

- [ ] `evals/fixtures/triage_labeled.json` — ~50 labeled emails, **committed
      before the first prompt is written** (design §6.5: fixtures written after
      a prompt get shaped to flatter it)
- [ ] `services/llm_client.py` — schema-forced call, retry-once, token logging
- [ ] Triage Pydantic schema + prompt (FR-3) · worker step 2
- [ ] `scripts/seed.py` — real: ~30 emails + policies
- [ ] `GET /metrics`, `MetricCards.tsx`, `UrgencyBadge.tsx`,
      `EmailFilters.tsx`, `CategorySuggestion.tsx`
- [ ] Category- and person-suggestion approval flows

---

## M4 — Reference data + retrieval

**Exit criterion:** `search_policies` on a road-repair query returns the
infrastructure policy first.

- [ ] `services/embeddings.py` — embedding API behind one module, hash-cached
- [ ] Embed-on-save for policies · worker step 4 (embed sent mail)
- [ ] Policies / people / categories CRUD + repositories
- [ ] Settings pages: policies, people, categories
- [ ] Both vector searches verified against known-similar seed data

---

## M5 — Draft agent + evals

**Exit criterion:** a seeded-topic email yields a draft citing the correct
policy; the trace shows the tool calls; the triage eval reports a baseline.

- [ ] `services/agent_tools.py` — the five FR-4 tools, each taking `user_id`
- [ ] `services/draft_agent.py` — hand-written loop, 10-turn cap, full trace
- [ ] System prompt (§6.3 rules: search before asserting, cite ids, never
      invent commitments)
- [ ] `POST /emails/{id}/draft` · worker step 3 · `DraftEditor.tsx`
- [ ] `evals/run_triage_eval.py` + first eval-driven prompt iteration

Largest milestone, and the one the project is judged on. Design §12's exit
criterion applies specifically here: every line of `draft_agent.py` must be
explainable in an interview.

---

## M6 — Consistency

**Exit criterion:** a seeded contradicting draft is flagged, with the policy
text cited.

- [ ] `services/consistency_service.py`, wired in as an agent tool
- [ ] `ConsistencyFlag.tsx` — advisory asides, never blocking
- [ ] `POST /consistency/scan` + results view
- [ ] `evals/fixtures/contradictions.json` (~15 pairs) + runner

---

## M7 — Hardening + initial ship

**Exit criterion:** a stranger can clone, seed, run, and understand it in
15 minutes — and a live demo URL exists.

- [ ] `tests/test_isolation.py` — two users × every resource type
- [ ] Failure-path tests · seed polish
- [ ] README: architecture diagram, eval results, run instructions
- [ ] Demo video
- [ ] Deploy: Vercel (frontend) + Railway/Render (API + worker + Postgres)

---

## M8 — AWS production deployment

**Exit criterion:** the full two-user flow works on the App Runner URL, RDS
holds the data, no secrets exist outside Secrets Manager, and the month's bill
is under the alert threshold.

- [ ] AWS Budget alert at $10 — **first action, before any resource is created**
- [ ] ECR repository + backend image pushed
- [ ] RDS Postgres 16 + `CREATE EXTENSION vector` + `alembic upgrade head`
- [ ] Secrets Manager entries for every env var (§9 list)
- [ ] App Runner service from the ECR image + IAM roles (ECR pull, secrets read)
- [ ] Production `MS_REDIRECT_URI` added to the Azure registration
- [ ] Frontend `NEXT_PUBLIC_API_URL` → App Runner · CloudWatch logs verified
- [ ] Smoke test: signup → connect → sync → triage → draft, in production
- [ ] README updated with the AWS architecture · Railway/Render decommissioned

Adds no application files — deployment configuration only. That is the payoff
of the all-config-via-`BaseSettings` rule: the same image runs in both
environments and only the source of the config changes.

---

## Scope control

If the schedule tightens, cut in this order — each costs little:
1. Demo video → a short unpolished screen recording.
2. M6 batch scan endpoint and its eval set (keep `check_consistency` as an
   agent tool — the in-agent path is the one that matters).
3. LLM-as-judge draft evals (the triage eval still yields a reportable number).
4. Frontend polish — shadcn defaults are fine.

Protect regardless: the agent loop and its persisted trace; two-user isolation
across every resource; one eval with a real number; a live URL.

---

## End-of-milestone checklist (every milestone)
1. **README touch-up** — update the status line and run instructions while the
   steps are fresh; add what is newly true (a screenshot once there is UI, eval
   numbers once M5 produces them). Writing these in the moment is the only way
   they stay accurate.
2. Update this file: check off the milestone, set the next position.
3. Log any design drift in `docs/decisions.md` AND in `ATTACHE_DESIGN.md`.

The full README — demo video, screenshots, architecture diagram, trade-offs —
is M7 work (design §13). Everything before that is keeping it honest.

## Resume checklist (start of each session)
1. `docker compose start` — bring the DB back up.
2. Read this file for the current position and next unchecked part.
3. Continue from there.

## Key decisions so far
Full log in `docs/decisions.md`.
- Dev runs Postgres in Docker with the API in a local `.venv` under
  `uvicorn --reload`; the Dockerfile is still built and tested from M1 so the
  M8 deploy holds no surprises.
- Commit granularity: one logical concern per commit (infra separate from docs).
- Production targets AWS (design v0.5, §3.4) with a deliberately minimal
  five-service footprint; expansion triggers are documented in §3.5.
