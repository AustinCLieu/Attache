# Design Decisions

Log of design drift: what changed, when, and why. Every entry here has a
matching change in `ATTACHE_DESIGN.md` (design doc §12 — "doc drift is a bug").

---

## 2026-08-30 — Production runs on AWS (design doc v0.5, new M8)

**Change.** Added M8, an AWS production deployment, after M7. The design doc
went from "AWS migration documented as future work" to a specified five-service
architecture: ECR (image registry), App Runner (runs the API + worker
container), RDS Postgres 16 + pgvector (production database), Secrets Manager
(production env vars), IAM (roles wiring those together), plus CloudWatch logs
(free, automatic from App Runner). §3.4 was rewritten as "Environments &
deployment"; §3.5 was added for expansion triggers.

**Why.** AWS deployment is now an explicit portfolio goal (§1.1) — it is the
piece of production engineering the project was otherwise missing.

**Why these five and no more.** Each service earns its slot by doing a job the
app already needs; nothing was added to lengthen the list. The deliberate
non-choices are the substance of the decision:

- **App Runner, not ECS/Fargate or EC2.** App Runner is the smallest thing that
  runs a container at a URL with HTTPS and rolling deploys — the same job
  Railway does in M7, so the migration is a swap, not a redesign. ECS/Fargate
  buys more control at the cost of substantially more configuration for an
  identical result at this scale. Kept in §3.5 as an optional later exercise.
- **Anthropic API direct, not Bedrock.** Keeps one LLM client across dev and
  production and avoids coupling the AI layer to the cloud provider. Trade-off
  documented in the README.
- **No DynamoDB.** The data is relational — foreign keys throughout, plus
  pgvector similarity search. A document store would be a worse design adopted
  only to look AWS-native.
- **Lambda, S3, EventBridge deferred to feature triggers** (§3.5): Lambda +
  EventBridge arrive with the Stripe/Graph webhooks, S3 arrives with email
  attachments. Services enter when their feature does.

**Why it costs no application code.** M8 adds zero application files — it is
deployment configuration only. All config already loads through
`BaseSettings`/env vars, so production differs only in where the values come
from (Secrets Manager instead of `.env`) and where the container runs. This is
now an explicit CLAUDE.md rule: no hardcoded URLs, hosts, or credentials.

**Cost control is a requirement, not an afterthought.** NFR-3 and M8's first
step both mandate an AWS Budget alert at $10 *before any resource is created*;
§14 adds stopping RDS between demo periods.

**Also in v0.5.** M7 renamed "initial ship" — Vercel + Railway/Render stays, as
a live demo URL reachable in an afternoon, and is decommissioned at M8. Shipping
to the easy platform first means AWS gets debugged against an app already known
to work.

---

## 2026-08-30 — CLAUDE2.md merged back into CLAUDE.md

**Change.** The v0.5 revision was drafted as a second root file, `CLAUDE2.md`.
Its additions (the AWS stack lines, the BaseSettings/env config rule, the
"update progress.md on every commit" rule) were merged into `CLAUDE.md` and
`CLAUDE2.md` was deleted. One instruction file again.

**Why.** `CLAUDE2.md` had dropped two things that would have silently changed
how sessions run: the `@docs/progress.md` import (a fresh session would not
load build state) and the entire Working style section (teach-as-we-go, explain
commands before running them, author-writes-the-code). Merging kept both.

**Related fix.** v0.5 had also re-embedded a full copy of CLAUDE.md inside
design doc §11, undoing commit `795b246`, which replaced that copy with a
pointer precisely because a duplicate drifts. It had already drifted — the
embedded copy was the CLAUDE2 version, missing Working style — leaving three
versions of the same instructions. §11 is a pointer again.

**Also.** `docs/PROGRESS.md` in the v0.5 text was normalized to the committed
filename `docs/progress.md` (lowercase). Windows is case-insensitive and would
have hidden this; git and Linux are not.

---

## 2026-08-30 — Learning model inverted: Claude writes, author reviews

**Change.** Claude Code now writes the code directly into files. The author
learns by reviewing it rather than by typing it. Replaces the previous rule
("the author writes all the code themselves; give code in chat"), and replaces
§12's role inversion, which had split the work — agent loop / OAuth / triage
schema hand-typed, CRUD and layouts delegated. There is no split now: Claude
writes all of it.

**What replaces the typing.** Every code delivery is paired with a walkthrough
written for a reader with no prior knowledge of the tooling: what the code does
and how, why it is built that way and what the alternatives were, and every
tool/package/keyword introduced — what it is, what it does for us, why it was
chosen. Depth scales with importance: the agent loop, OAuth flow, and triage
schema get line-by-line treatment; CRUD and layouts get a summary.

**Why.** Author's call. The typing was the bottleneck against a 10-day finish
and it was not where the learning actually lived — reading a well-explained
implementation teaches the design, which is what §12's exit criterion tests.

**What does not change.** §12's exit criterion stands: the author must be able
to explain every line of `draft_agent.py` in an interview. That now depends
entirely on the quality of the walkthroughs, which makes them a deliverable
rather than a courtesy. Code is written for readability over cleverness, since
the review is where the learning happens.
