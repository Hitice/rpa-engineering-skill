# Architecture, Idempotency and Observability

This reference is loaded only when the current step needs the deeper rules behind the skill. It complements `SKILL.md` and never duplicates its checklists.

## Layered boundaries

```
core/         depends on   standard library + pydantic for value objects
contracts/    depends on   core entities only (pure domain types)
adapters/     depends on   contracts + core entities + framework libraries
flows/        depends on   core + contracts + adapters
```

Enforced rules:

- `core/` is import-pure: only standard library, typing, dataclasses and `pydantic` for value objects. Never `selenium`, `httpx`, `os`, `requests`, `boto3`, etc.
- `contracts/` declare Protocols/ABCs in domain terms; they may reference pure entities from `core/` but never framework types.
- `adapters/` implement contracts and own all IO. They translate domain calls to library-specific calls and back.
- `flows/` instantiate adapters, inject them through contracts into `core/` services and orchestrate the use case.
- A new adapter (e.g., swapping Selenium for Playwright, or adding an API path) must not require changes in `core/`.

## Contracts (Protocols)

Contracts live in `contracts/` and use `typing.Protocol` or `abc.ABC`. They:

- expose only domain-meaningful operations (`open_session`, `submit_invoice`, `download_report_for(date)`)
- never expose framework types (`WebElement`, `Response`, `Connection`)
- raise domain exceptions (`AuthenticationError`, `ElementTimeoutError`, `BusinessRuleViolation`)

## Configuration model

All runtime values are externalized:

- URL, credentials, browser, headless mode, default and per-step timeouts, retry budget, output paths, correlation id provider, log level
- loaded with `pydantic-settings` from environment, with a typed schema and defaults
- `.env.example` is committed; `.env` is gitignored
- secrets are never logged

## Idempotency patterns

Pick the pattern per use case before coding:

- **Create with natural key**: query by domain key first; only create if absent. Return the existing entity otherwise.
- **Upsert with state diff**: read current state, compute minimal change set, apply only divergent fields.
- **Token-based once**: persist a processed `correlation_id` set; skip when seen.
- **Compensating action**: if a step is non-idempotent at the source, pair it with a deterministic check that detects partial application and reconciles.

Files:

- compute a content hash before upload; skip if the same hash already exists at the destination.
- when downloading, write to a temp path and atomically rename only after integrity check.

## Persistent state and the StateStore contract

A `StateStore` keeps the per-key lifecycle across runs. Without it, two consecutive runs may produce duplicates whenever the destination's existence check is eventually consistent or unavailable.

Required surface:

```python
class StateStore(Protocol):
    def get(self, key: str) -> ItemState | None: ...
    def upsert(self, state: ItemState) -> None: ...
```

Item lifecycle:

```
PENDING ──▶ IN_PROGRESS ──▶ SUCCESS                          (terminal)
                          ▶ FAILED ──▶ ... ──▶ DEAD_LETTER   (terminal at max_attempts)
                          ▶ SKIPPED                          (non-terminal, re-validated)
```

Rules:

- *Terminal* states are exactly `SUCCESS` and `DEAD_LETTER`. They short-circuit the UI: subsequent runs do not consult the browser for those keys.
- `SKIPPED` is intentionally **non-terminal**. It records that a previous run observed the record at the destination, but the destination is the source of truth and may be eventually consistent. Every run re-validates via `record_exists`; if the destination no longer has the item, the bot proceeds to submit. The cost is one read per previously-skipped key per run, in exchange for correctness against rollbacks, manual deletions and replication lag.
- `FAILED` is also non-terminal: it is the natural input to the next attempt, until `attempts >= max_attempts` promotes it to `DEAD_LETTER`.
- `attempts` is incremented per cross-run attempt, never per intra-call retry.
- `dry_run` never persists state mutations.
- Storage backend is interchangeable: SQLite for single-host bots, Postgres or Redis for fleets. Pick the smallest store that meets the consistency need.
- Schemas evolve with explicit migrations; never silently widen columns or change semantics.

## Dry-run

Dry-run is **online by design**. The flow:

- acquires the process lock
- opens a real browser session and performs the login
- traverses the existence check for every record
- never submits, never writes the state store, never produces external side effects
- emits each suppressed write as `status="skipped"` with `output_summary={"would_apply": true, ...}` so log consumers stay on the documented `success | error | skipped` enum
- exits with the same status codes as a real run

This makes dry-run a useful pre-deployment smoke against the real target. Continuous integration never invokes dry-run: CI runs the unit suite with fake adapters; live connectivity is exercised by the `integration` test marker, opted in via the same environment variables a real run uses.

## Redaction policy

The structured logger redacts sensitive payload fields. The contract:

- a curated default list (`password`, `token`, `secret`, `api_key`, `apikey`, `authorization`, `cookie`, `cpf`, `cnpj`, `ssn`, `credit_card`) ships in `Settings.redact_keys`
- override declaratively via the `RPA_REDACT_KEYS` env variable as a comma-separated list
- match rule is case-insensitive substring on the *key*; values become `"***"`
- redaction descends recursively into nested dicts and lists in `input_summary` and `output_summary`
- free-text fields (`error_message`, `input_summary["url"]`, etc.) are **not** auto-redacted; redact at the source whenever the call site might emit secrets in narrative form
- redaction is a defense-in-depth control. The first defense is to never put raw secrets into logging summaries.

## Process lock and orchestration

A single-instance lock prevents two runs from racing on the same destination. Use a file lock for one host or a distributed lock (Redis, etcd, Postgres advisory) for clusters.

The flow layer is the single place that:

- acquires the process lock with a bounded timeout
- opens the state store
- builds adapters and injects them through contracts into core
- writes the run summary log

Scheduling is delegated. The bot is a single-shot, idempotent program; the trigger is cron, Task Scheduler, systemd timer, Kubernetes CronJob or a workflow engine.

## Retry policy

- Retry only on transient, classified errors (network, `ElementTimeoutError`, `StaleElementReferenceException`, 5xx).
- Never retry on `BusinessRuleViolation`, `AuthenticationError`, 4xx other than 408/429.
- Bounded budget per step (attempts + total wall time), exponential backoff with jitter.
- Each retry must log attempt number, reason, and the delay applied.

## Observability schema

Every step emits one structured record:

```json
{
  "timestamp": "ISO-8601",
  "process": "string",
  "correlation_id": "uuid",
  "step": "string",
  "status": "success | error | skipped",
  "duration_ms": 0,
  "attempt": 1,
  "input_summary": {},
  "output_summary": {},
  "error_type": "string?",
  "error_message": "string?"
}
```

Rules:

- `input_summary` and `output_summary` contain only non-sensitive fields; redact tokens, full names, document numbers as configured.
- On error, also persist `page_source` and a screenshot to a per-execution artifact folder, with the same `correlation_id`.
- A run finishes with a summary record: totals for `success`, `error`, `skipped`, plus elapsed time.

## Error taxonomy

Define and use these in `core/` and surface them from adapters:

- `ConfigurationError` — invalid or missing configuration
- `AuthenticationError` — credentials/session
- `AuthorizationError` — permission denied
- `ElementTimeoutError` — waiting for a UI condition exceeded budget
- `IntegrationError` — external system failure (network, 5xx, malformed response)
- `BusinessRuleViolation` — domain invariant violated
- `IdempotencyConflict` — divergent state where reconciliation is unsafe

Each one carries `step`, `correlation_id` and a redacted context.

## Selectors and Page Objects

- One Page Object per logical screen.
- Selectors centralized as class attributes; never inlined in flow code.
- Preference order: `data-testid` ⟶ stable id ⟶ ARIA role/name ⟶ stable CSS ⟶ relative locator. Avoid full XPath and positional selectors.
- Page Objects expose intentions (`login(user, password)`, `open_invoice(id)`), never raw elements.

## Testing strategy

- **Unit tests** target `core/`: deterministic, no IO, run in milliseconds.
- **Integration tests** target adapters: use a controllable site (a local fixture or a stable public sandbox), `Options.add_argument("--headless=new")`, short explicit waits, no `sleep`.
- **Contract tests** assert that any adapter implementing a contract satisfies the same behavioral expectations. Add one per contract.
- **Smoke flow** runs a happy-path use case in dry-run on every CI build.

## Definition of done

A change is done only when all of the following hold:

- spec, plan and architecture documented in the PR description
- no `sleep`, no hardcoded values, no forbidden libraries
- tests added for changed behavior; existing tests still pass
- dry-run executed and its log attached to the PR
- structured logs cover every step
- review questions in `SKILL.md` answered explicitly
