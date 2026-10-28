# Technical Challenge Audit — Contractor ↔ HR Unique-Code (کد یکتا) Workflow

**Prepared by:** Senior Software Architect / Technical Auditor
**Date:** 2026-06-20
**Scope:** End-to-end failure-mode analysis of the contractor statement (صورت وضعیت) process and the HR-admin code-issuance (صدور کد یکتا) workflow, their integration seam, the PostgreSQL/Docker substrate, and the planned UI overhaul.
**Method:** Direct inspection of the running codebase (FastAPI backend, React/Vite frontend, Alembic migrations, docker-compose.yml). Every finding below cites the actual file and symbol it derives from. Severity tags: **[CRITICAL]** data loss / financial incorrectness / silent corruption, **[HIGH]** broken business logic or security, **[MED]** operational fragility, **[LOW]** hygiene.

---

## 0. The single most important finding: there is no *one* workflow — there are *three*, and they disagree

The brief assumes one contractor process and one 4-stage HR code-issuance process that are merely *misaligned*. The code reveals something more serious: **"the 4-stage workflow" is an overloaded phrase that maps to at least three independent, separately-coded state machines that share neither a status vocabulary nor a transactional boundary.**

1. **The contractor progress-statement machine** — `app/services/statement_service.py`. A 4-stage approval ladder, enum `ProgressStatementStatus`: `DRAFT -> PENDING_L1 -> PENDING_L2 -> PENDING_L3 -> PENDING_L4 -> APPROVED` (plus `REJECTED`, `BOOKED`). This is what most people *call* "the 4 stages."

2. **The HR funding-letter machine** — `app/services/workflow_service.py`, enum `FundingStatus`. This is **not** 4 stages — it is an **11-state** chain: `PENDING_VP_PLANNING -> PENDING_VP_FINANCE_REVIEW -> BUDGET_WELFARE_DEPT -> BUDGET_GM_HC -> BUDGET_FINANCE_UNIT -> BUDGET_VP_FINANCE -> CHARGE_LETTER_REGISTERED -> PENDING_FINAL_CHARGE -> FINAL_APPROVED -> CHARGING_IN_PROGRESS -> COMPLETED` (+ `REJECTED`), carrying *five additional legacy states* still live in the enum.

3. **The volume-contract / Yekta-issuance machine** — `app/services/yekta_service.py`, expressed as **step order indices 101->102->103->104** (`VOLUME_BASE_STEP_NUMBER … VOLUME_GENERATION_STEP_NUMBER`). *This* is the genuine 4-stage code-issuance flow that actually mints the 11-segment کد یکتا.

The "workflow mismatch" the brief describes is therefore not a synchronization bug to be patched — it is an **ontological mismatch**: three subsystems were authored at different times (visible in git history and in the `# Legacy statuses` comment block at `models.py:1311+`), each invented its own notion of "a statement" and "a stage," and they are stitched together by *denormalized string fields and JSON blobs* rather than foreign keys. Every concrete failure mode below is a symptom of this root cause.

### The two incompatible definitions of "statement"

- The contractor ladder operates on the **`progress_statements`** table (`ProgressStatement`, `models.py:1148`), linked to `Transaction` by a real FK: `Transaction.progress_statement_id` (`models.py:431`) — described in-code as the "Golden Thread."
- The Yekta issuer operates on **`EntityDocument`** rows discovered *by string match* — `document_type in {APPENDIX_5_TIMESHEET, MONTHLY_TIMESHEET, CONTRACTOR_STATEMENT_UPLOAD}` joined to a `WorkflowStep` whose `order_index == 102` (`yekta_service._latest_statement_document`).

These are two **disjoint** representations of the same real-world صورت وضعیت. A grep confirms there is **no foreign key linking `FundingRequest` to either `ProgressStatement` or `CivilProject`** — the HR funding letter is an island. Consequently "cross-panel communication" is not implemented as referential integrity at all; it is implemented as *convention*, and conventions drift.

---

## 1. Frontend-to-Backend Flow (and vice versa)

### 1.1 State-management flaws synchronizing the stages

**[CRITICAL] The two ladders advance independently with no shared transaction or correlation key.**
`statement_service.approve_statement` (locks the row `with_for_update()`, line 488) walks `PENDING_L1…L4 -> APPROVED` and on approval auto-creates a `Transaction` with `unique_code=None` (line 390, explicitly NULL by design — see the loud `WARNING` at `models.py:382`). Separately, `YektaService.issue_for_approved_volume_statement` mints the real code and **also** creates/overwrites a `Transaction` keyed on a *string* `tracking_number` of the form `CIVIL-{project}-DOC-{doc}-EVT-{nn}` (`yekta_service._tracking_number`). Nothing guarantees these two Transaction-creation paths refer to the same payment. There are **10 distinct `Transaction(...)` construction sites** across the backend (`yekta_service`, `statement_service`, `civil_financial_bridge`, `budget_service`, `attendance_service` x2, `portal.py`, `transaction_adapter`). Each invents its own tracking_number/unique_code discipline. The frontend stepper therefore renders a "stage" that is a *projection* of whichever table that panel happens to query — the contractor panel reads `progress_statements.status`, the HR/Yekta panel reads `EntityDocument.payload` + `FinancialMatrix.payment_queue_status`. **They can show contradictory stages for the same logical statement and neither is "wrong" against its own source.**

**[HIGH] Status is modeled as a free-text `String`, not an enforced enum, on the most-written table.**
`ProgressStatement.status` for the legacy path is `Column(String, default="DRAFT", index=True)` (`models.py:397`) — the docstring even lists `BOOKED` as a valid value that does **not** appear in `VALID_TRANSITIONS` (`statement_service.py`). A typo, a stale client, or a second code path can write any string; the state machine only guards transitions it *recognizes*. The newer `ProgressStatement` definition uses `Enum(ProgressStatementStatus)` (line 1228) — meaning **the same table is described two ways in the same file**, a classic legacy-migration artifact. Frontend state derived from a column that is sometimes a typed enum and sometimes arbitrary text cannot be reliably synchronized.

**[HIGH] Frontend has no server-state cache or reconciliation layer.**
`frontend/package.json` shows **`zustand` but zero `@tanstack/react-query`/SWR** (confirmed: react-query usage count = 0). There are **34 raw `fetch(` call sites** and 575 files using `useState/useEffect`. Every panel holds workflow state in *local component state*, fetched imperatively, with no shared invalidation. When the HR panel advances a stage, the contractor panel's `useState` copy is stale until a manual refresh. There is no optimistic-rollback, no `staleTime`, no refetch-on-focus — so the "state management failure" in the brief is structurally guaranteed, not incidental.

### 1.2 API-contract mismatches & payload validation

**[CRITICAL] The Yekta stage trusts an untyped JSON blob, not a Pydantic schema.**
The 11-segment code is built from `EntityDocument.payload` — a free-form JSON column. `YektaService._normalize_yekta_payload` re-implements validation *by hand* (`required_fields = [...]`, manual `missing` checks, `raise ValueError`). This bypasses FastAPI's schema validation entirely: errors surface as `ValueError` (HTTP 500) rather than 422, the contract is undocumented in OpenAPI, and the frontend cannot know the required shape except by trial and error. The gross statement amount is even *inferred heuristically* — if no `statement_total_amount` is present, `_extract_gross_statement_amount` opens the uploaded xlsx/xls, scans **every cell**, and takes `max(candidates >= 10000)` as the amount. **A spreadsheet containing any large unrelated number silently becomes the payment basis.** This is a financial-correctness landmine.

**[HIGH] Duplicate/overloaded route definitions create ambiguous contracts.**
`funding_workflow.py` stacks three decorators on one handler — `/requests/{id}/transition`, `/{id}/transition`, `/requests/{id}/advance` all map to `advance_request`; `create_request` answers both `/requests` and `/`; `get_request_detail` answers `/requests/{id}` and `/{id}`. Overlapping path templates (`/{request_id}` vs `/inbox`, `/all`, `/archive`) invite **route-shadowing** depending on registration order. The contract is not single-sourced.

**[HIGH] `extra_fields` is a server-side allow-list, silently dropping everything else.**
`WorkflowService.advance_status` copies only keys in `UPDATABLE_EXTRA_FIELDS` (incl. `amount`, `budget_code`, `charge_letter_number`…). Any other field the frontend sends on a transition is **silently discarded** — no 422, no warning. A renamed or new field on the client vanishes without trace, among the hardest integration bugs to diagnose.

### 1.3 Asynchronous race conditions between the two panels

**[CRITICAL] Cross-machine race: contractor approval and Yekta issuance are not mutually serialized.**
`workflow_service.advance_status` takes a row lock on `FundingRequest`; `statement_service` takes a row lock on `ProgressStatement`. But the Yekta issuer locks **neither** — it reads `EntityDocument`/`FinancialMatrix` and writes `Transaction`. So "Contractor updates status while HR generates the unique code" (the brief's exact scenario) involves **two different rows in two different tables under two different (or absent) locks**. There is no advisory lock spanning the logical operation. Two concurrent issuance calls for the same project can both pass the uniqueness probe and race on insert (see 2.3).

**[MED] Tracking-number generation has a check-then-insert TOCTOU.**
`funding_service._generate_tracking_number` does `max(id)+1` then formats `HR-{year}-{nnnn}`; the row is not inserted under that lock. Two concurrent creates compute the same `max(id)` -> same tracking number -> one wins the `unique=True` constraint (`models.py:1372`) and the other throws an unhandled `IntegrityError` (HTTP 500) instead of retrying. Same pattern in `statement_service._generate_tracking_number`.

---

## 2. Database & Docker Infrastructure

### 2.1 Legacy schema vs. new panel requirements

**[CRITICAL] Dual table-definitions and a 24-file migration chain encode unmanaged legacy debt.**
`models.py` contains **two descriptions of `ProgressStatement.status`** (free `String` at line 397, typed `Enum` at line 1228) and `FundingStatus` openly carries **five legacy states** (`DRAFT, PENDING_VP_FINANCE_INITIAL, PENDING_BUDGET_ALLOCATION, PENDING_VP_FINANCE_FINAL, APPROVED_FOR_CHARGE`) that the *current* `TRANSITION_MAP` cannot produce or consume. Old rows can sit in states the engine has no transitions for — they become **permanently stuck** and invisible to `get_inbox` (which only returns `ROLE_VISIBLE_STATUSES`). The Alembic chain includes telling names: `9a14173679c5_add_sent_to_finance_status_and_unique_`, `f4d3c7a9b21e_add_pending_unique_code_to_workflow_status`, `b7c4d9e2f103_update_civil_workflow_to_revised_chart` — i.e., the workflow *chart itself* has been rewritten via migration, so historical rows were defined under a different graph than today's code enforces.

**[HIGH] The 11-segment کد یکتا embeds business meaning the schema does not protect.**
`yekta_codes.build_yekta_segments` composes 11 fields (zone/dept/section/budget/cost-center/continuous-action/activity-hash/beneficiary-hash/event/year/sequence). Two are **MD5 hash fragments** of free text: `special_activity_hash = md5(...)[:3]` and `beneficiary_hash = md5(...)[:6]`. A 3-hex space is **4096 values** and a 6-hex space ~16.7M — collisions across different activities/beneficiaries are expected at scale, and when they collide the *prefix* used for de-duplication (`prefix_matches`) treats two genuinely different events as the same code family. Mapping this legacy code onto new panel filters ("show all codes for beneficiary X") is unsafe because the code is lossy by construction.

**[MED] PostgreSQL is mandated by config but the working DB is SQLite.**
`app/database.py` *hard-fails* unless `DATABASE_URL` starts with `postgresql` (`raise RuntimeError`), yet a `municipality_demo.db` SQLite file (720 KB) sits in the repo root and is referenced by ad-hoc scripts. This split means **migrations, `with_for_update()` locking semantics, JSON column behavior, and case-sensitivity are all tested against the wrong engine**. SQLite ignores `SELECT … FOR UPDATE` silently — so every locking guarantee above is *unverifiable* in dev and only "works" in prod.

### 2.2 PostgreSQL-in-Docker risks

**[HIGH] Pool sizing vs. uvicorn workers is a latent connection-exhaustion bug.**
`_build_engine` sets `pool_size=5, max_overflow=10` -> max 15 connections **per process**. Under multiple uvicorn workers (the docstring targets "multi-worker production deployments") that multiplies: 4 workers x 15 = 60, plus the engine opens an eager validation connection at import (`with engine.connect(): SELECT 1`). `postgres:15-alpine` defaults to `max_connections=100` with no pgbouncer/Redis-backed pooling configured (Redis is present in docker-compose but unused by the DB layer). "High I/O panel updates" — many small status-advance writes — will saturate the pool, and with no statement timeout set, a single long-held `with_for_update()` lock can cascade into pool starvation.

**[HIGH] Volume persistence and migration are operationally fragile.**
`docker-compose.yml` uses a named volume `postgres_data` with `restart: always` and **no healthcheck, no backup, no init/migration step**. Alembic is invoked out-of-band, so a fresh `docker compose up` yields an *empty* schema until someone manually runs `alembic upgrade head`; there is no `depends_on: condition: service_healthy` gating the app, so the backend's import-time `SELECT 1` can crash on a not-yet-ready DB (cold-start race). `version: '3.8'` is obsolete. Credentials are `postgres/postgres` in cleartext.

**[MED] No connection-recycle or timeout hardening.**
`pool_pre_ping=True` is set (good), but there is no `pool_recycle`, no `connect_args` statement/lock timeout, and `echo=False` with no slow-query logging. In Docker, idle keepalive drops plus a missing `pool_recycle` produce intermittent "server closed the connection unexpectedly" under low traffic.

### 2.3 Data-integrity & concurrency when contractor updates status while HR generates the code

**[CRITICAL] The uniqueness guarantee for کد یکتا is a non-atomic check-then-act across THREE tables.**
`YektaService._next_available_yekta_code` loops: build candidate -> probe `FinancialMatrix.yekta_code`, `Transaction.unique_code`, **and** `CivilProject.yekta_code` for absence -> if all clear, return it. **There is no lock and no insert inside the loop.** Between the probe and the eventual `flush()`, a concurrent issuance can pick the *same* sequence and the same code. The DB-level `unique=True` on `Transaction.unique_code`/`FinancialMatrix.yekta_code` then rejects the loser with an `IntegrityError` that is **not caught** anywhere in `issue_for_approved_volume_statement` -> HTTP 500, partial writes already flushed, and a `FinancialMatrix` row possibly left with `payment_queue_status=READY_FOR_PAYMENT_QUEUE` but no valid transaction. The check spans three tables but enforcement spans one — that gap is the bug.

**[CRITICAL] Audit log is transactional in one engine and best-effort in the other.**
In `workflow_service.advance_status`, the `FundingWorkflowLog` is added and committed *with* the status change — atomic. But `yekta_service` writes **no workflow log at all** for code issuance; the only trace is `payload["yekta_issued_at"] = datetime.utcnow()` stamped into a JSON blob (`_sync_statement_payload`). So the financially-critical act of minting a payment code is **not audited** in any queryable, tamper-evident table — it is buried in a mutable JSON field that the next issuance overwrites. For a municipal finance system this is an audit-defensibility failure.

**[HIGH] Idempotency is asymmetric and partly accidental.**
Yekta issuance is *re-runnable* by design (upserts `FinancialMatrix` by `(project, statement_document, financial_event)`, upserts `Transaction` by `tracking_number`) — but it also does `project.yekta_code = None` at the end and recomputes codes if the prefix no longer matches. So **re-issuing after any org/budget edit mints brand-new codes and orphans the old `Transaction.unique_code` values** (still present, still unique-constrained, now dangling). Meanwhile the contractor `Transaction` created at statement-approval (`unique_code=None`) and the Yekta `Transaction` are **never reconciled** — two transaction lineages accumulate for one payment.

**[HIGH] `reject` releases budget by side-effect with no compensation linkage.**
`advance_status` calls `BudgetService.release_budget(req.budget_code)` on reject and `reserve_budget` on the `BUDGET_VP_FINANCE->approve` edge. These budget mutations live in a *different service* with its own persistence; if the subsequent `db.commit()` of the status change fails, the reservation/release may already have occurred -> **budget ledger and workflow state diverge** with no outbox/saga to repair them.

---

## 3. Frontend UI/UX Refactoring Risks

**[HIGH] The UI is the de-facto integration contract, so a visual overhaul is a logic overhaul.**
With no react-query layer and **34 imperative `fetch()` sites** across ~30 funding/statement/wizard components, each component encodes (a) the endpoint, (b) the payload shape the untyped backend silently expects, and (c) stage-derivation logic locally. Ripping out the "ugly" markup risks deleting the `useEffect` that happens to refetch after a transition, or the hand-built payload that satisfies `_normalize_yekta_payload`'s manual validation. **There is no typed client to lean on** — `src/services/api.ts` uses same-origin relative URLs and bare fetch; the contract lives in components.

**[MED] Mixed React typings and a half-migrated component set.**
`package.json` pins runtime `react@^18.3.1` but devDeps `@types/react@^19.x` — a known source of subtle JSX/ref type breakage during refactor. A stray `AggregationDashboard.tsx.backup` and a `figma` component tree alongside hand-built ones indicate an in-flight design migration. Overhauling on top of an unfinished migration compounds risk.

**[MED] Stage UI is rendered from whichever table the panel queries — redesign can desync display from source.**
The contractor stepper reads `ProgressStatementStatus`; the Yekta wizard reads step `order_index` (101–104) + `FinancialMatrix.payment_queue_status`; the HR letter inbox reads the 11-state `FundingStatus` filtered by `ROLE_VISIBLE_STATUSES`. A unified "new" UI trying to present *one* progress bar must pick a source of truth that **does not exist** in the data model. Any naive consolidation will display a stage that is true for one machine and false for another.

**Refactor guardrails (solutions-oriented):**
1. **Freeze the contract first.** Introduce a typed API client + Pydantic-strict request schemas for the Yekta payload *before* touching markup, converting `_normalize_yekta_payload`'s manual checks into a 422-returning schema.
2. **Adopt server-state caching** (react-query/SWR) so refetch/invalidation is centralized, not hidden in per-component `useEffect`. Removes the 1.1 staleness class directly.
3. **Characterization tests at the seam** — golden tests on `issue_for_approved_volume_statement` and `advance_status` so a visual rewrite cannot silently change financial output.
4. Strangler pattern, panel-by-panel, behind a feature flag — never a big-bang reskin over a 3-machine integration.

---

## 4. Prioritized remediation (root-cause first)

1. **[CRITICAL] Establish one canonical link** between `FundingRequest`/`ProgressStatement`/`EntityDocument` (real FKs + a correlation id), replacing string/JSON convention. Until this exists, every sync fix is a patch on sand.
2. **[CRITICAL] Make code issuance atomic and audited** — DB sequence or `INSERT … ON CONFLICT` for the Yekta sequence segment (drop the check-then-act loop), wrap issuance in one transaction, write a real `YektaIssuanceLog` row, not a JSON timestamp.
3. **[CRITICAL] Replace heuristic amount inference** with an explicit, validated `statement_total_amount` contract; never derive a payment basis from `max()` of arbitrary spreadsheet cells.
4. **[HIGH] Collapse status modeling** to a single typed enum per machine; migrate or quarantine legacy `FundingStatus`/string-status rows.
5. **[HIGH] Verify locking on real PostgreSQL** (kill the SQLite divergence), add statement/lock timeouts, right-size the pool to worker count, add a Compose healthcheck + gated migration step, rotate the cleartext `postgres/postgres` credentials.
6. **[HIGH] Introduce a typed API client + server-state cache** as the precondition for any UI overhaul.

---

## Hidden assumptions this audit surfaced

- *Assumed:* "the 4-stage workflow" is one thing. *Reality:* three machines (4-stage statement ladder, 11-state funding chain, 101–104 Yekta steps).
- *Assumed:* panels communicate via the database. *Reality:* via denormalized strings and JSON payloads, with no FK between the funding letter and the civil/statement world.
- *Assumed:* unique codes are guaranteed unique. *Reality:* guaranteed by a non-atomic 3-table probe + lossy MD5 segments.
- *Assumed:* PostgreSQL is the system of record. *Reality:* config demands Postgres while a SQLite file is the de-facto dev DB, invalidating all concurrency testing.
- *Assumed:* issuance is audited. *Reality:* the funding chain is audited; the actual code-minting step is not.
