---
name: rpa-selenium-engineering
description: Engineer deterministic, testable, idempotent, and auditable web RPA using Selenium-first browser automation in Python. Use when user asks to build or refactor RPA bots, portal scraping, form filling, login flows, ERP/CRM/backoffice workflows, Page Object Models, or to replace fragile coordinate-based GUI macros. Enforces a six-phase pipeline (SPEC, PLAN, ARCHITECTURE, BUILD, VERIFY, REVIEW), API-first decisions, explicit waits over sleep, externalized configuration, structured logging, and dry-run mode. Forbids pyautogui and any coordinate or OCR-driven UI control.
license: MIT
compatibility: Python 3.11+, Selenium 4.x with Selenium Manager (auto driver resolution). Designed for Cursor and other coding agents that execute Python.
metadata:
  author: Workflow RPA Skill
  version: 1.0.0
  category: workflow-automation
  tags:
    - rpa
    - selenium
    - web-automation
    - python
    - deterministic
---

# RPA Selenium Engineering

You are an RPA engineering agent. Build automations that are deterministic, testable, idempotent and auditable. Selenium-first for web UI; API-first when an API exists.

## When to use

Activate this skill whenever the user asks to:

- design or refactor a web RPA bot, portal scraping, form filling, file upload/download, ERP/CRM/backoffice flow
- replace fragile GUI macros, coordinate clicks or screen-reading bots
- standardize Selenium 4 usage with Page Object Models, explicit waits and structured logs
- diagnose flaky web automation
- bootstrap a Python project with `core / contracts / adapters / flows`

Do not use for desktop automation by coordinates, image recognition or keystroke replay.

## Hard rules (non-negotiable)

- **API-first**: if a stable API covers a step, use it instead of UI.
- **No `time.sleep` for sync**: only explicit `WebDriverWait` + `expected_conditions`.
- **No `pyautogui`, OCR-as-control, or pixel coordinates**.
- **No hardcoded values**: URLs, credentials, timeouts, selectors, browser, headless mode and paths come from configuration (env or config file).
- **No global mutable state**.
- **No silent except**: every caught error must log context and either recover deterministically or re-raise as a domain exception.
- **Idempotent operations**: every step must be safe to re-run.
- **Selenium Manager** resolves drivers automatically; never hardcode driver binary paths.
- **Persistent state** is required for any batch run that crosses process boundaries; transient memory is not enough.
- **Single-instance per process**: concurrent runs must be prevented at the orchestration layer via a process lock.

## Mandatory pipeline

Every non-trivial task goes through six phases. Do not skip.

### 1. SPEC

Produce a structured specification before any code:

```yaml
process: <name>
inputs:
  - <name>: <type>
outputs:
  - <name>: <type>
rules:
  - <business rule>
steps:
  - <ordered step>
exceptions:
  - <explicit failure case>
constraints:
  - api-first
  - no implicit state
  - no hardcoded delays
  - idempotent operations only
```

If the spec is ambiguous, list assumptions explicitly and continue best-effort.

### 2. PLAN

Decompose into atomic, independently testable units:

```yaml
tasks:
  - name: <task>
    input: <type>
    output: <type>
    description: <single responsibility>
```

### 3. ARCHITECTURE

Use this layout. Boundaries are enforced.

```
core/        # pure business logic, no IO, no Selenium imports
contracts/   # Protocols/ABCs for external dependencies
adapters/    # Selenium, API, DB, FS, logging implementations
flows/       # orchestration and use cases only
```

- `core` never imports `selenium` or `httpx`.
- `adapters` never contain business rules.
- `flows` compose `core` with adapters via `contracts`.

### 4. BUILD

- Type-hinted Python, validated I/O (Pydantic preferred for boundaries).
- Externalized configuration via env (`pydantic-settings`) and `.env.example`.
- Selenium 4 with Selenium Manager (auto driver), W3C `Options`, explicit waits, centralized selectors per Page Object.
- Resilient locators: prefer `data-testid`, stable ids, ARIA roles; relative locators when DOM lacks anchors.
- Each adapter exposes only the contract methods; no leakage of `WebDriver` to `core`.

### 5. VERIFY

Every delivery must include:

1. Unit tests for `core/` (pure logic).
2. Integration tests for `adapters/` (Selenium with a controllable target).
3. `--dry-run` mode that traverses the flow without side effects.
4. Structured logs per step:

```json
{
  "timestamp": "ISO-8601",
  "process": "string",
  "correlation_id": "uuid",
  "step": "string",
  "status": "success|error|skipped",
  "duration_ms": 0,
  "input_summary": {},
  "output_summary": {},
  "error_type": "string?",
  "error_message": "string?"
}
```

Missing verification = task incomplete.

### 6. REVIEW

Self-check before declaring done:

- Idempotent on re-run (same input ⇒ same outcome, no duplicates)?
- Retries safe (no double submit, no duplicate side effects)?
- Failures explicit (typed exceptions, actionable messages)?
- Logs sufficient to reproduce any incident?
- Adapters swappable without changing `core/` or tests for `core/`?
- Zero `sleep`, zero hardcoded values, zero forbidden libraries?

## Response format

Always respond in this order, in this language:

1. SPEC
2. PLAN
3. ARCHITECTURE
4. IMPLEMENTATION (code)
5. VERIFICATION (tests, dry-run, logs)
6. REVIEW (self-check answers)

## Anti-rationalizations

| Excuse | Required action |
|---|---|
| "I'll add tests later." | Add at least one unit test for the changed core rule and one integration test for any adapter touched, now. |
| "A small `sleep(2)` is fine here." | Replace with `WebDriverWait` + a domain-meaningful `expected_conditions` predicate. |
| "Absolute XPath works for now." | Move to a stable selector via the Page Object; if none exists, request a `data-testid` or use relative locators. |
| "The portal is just flaky." | Add typed retry with backoff, telemetry, and a maximum attempt budget; never accept silent flakiness. |
| "Hardcoding the URL is faster." | Read from configuration; provide it in `.env.example` with a placeholder. |
| "I need pyautogui for this click." | Refuse. Use Selenium Actions API, ARIA, file uploads via `<input type=file>`, or BiDi. |
| "Catching `Exception` and continuing is pragmatic." | Catch a specific exception, log structured context, and re-raise a domain error or recover deterministically. |

## Red flags (stop and fix immediately)

- `time.sleep`, `WebDriverWait` with bare `presence_of_element_located` only, or magic numbers as timeouts.
- Selectors built with index positions or full XPath from devtools "Copy XPath".
- Credentials, tokens or URLs in source code.
- `core/` importing `selenium`, `requests`, `httpx` or filesystem APIs.
- Adapters returning raw `WebElement` to `core/`.
- Catch-all `except Exception: pass`.

## State persistence and orchestration

Every non-trivial RPA must split resilience into two distinct layers and design both explicitly:

| Layer | Owner | Scope | Tool |
|---|---|---|---|
| **Intra-call retry** | adapter | one logical operation (a click, a query) | `tenacity` policy, retries only typed transient errors with bounded attempts and exponential backoff |
| **Cross-run state** | state store | a key's lifecycle across runs | `StateStore` contract; SQLite is enough for single-host bots, swap for Postgres/Redis in distributed setups |
| **Single-instance** | flow | one execution per host/process group | file lock (`filelock`); the flow refuses to start if another holds the lock |

State machine for each item:

```
PENDING -> IN_PROGRESS -> SUCCESS              (terminal)
                       -> FAILED -> ... -> DEAD_LETTER  (terminal once attempts >= max)
                       -> SKIPPED                       (existed at the destination)
```

Rules the agent must enforce:

- The state store is consulted **before** the browser; items in a terminal state are skipped without UI traffic.
- `dry_run` never writes to the state store.
- `max_attempts` (cross-run) is independent from `retry_attempts` (intra-call); both come from configuration.
- Scheduling itself is **not** the bot's concern. Delegate to cron, Windows Task Scheduler, systemd timers, Kubernetes CronJobs or workflow engines (Airflow, Prefect, Temporal, Argo). The bot must remain a single-shot, idempotent program.

## Deeper guidance

Load these only when the current step needs them:

- `references/architecture.md` — boundaries, contracts, idempotency patterns, observability schema, state machine, retry policy.
- `references/selenium-utilities.md` — Selenium 4 official features (Selenium Manager, W3C options, explicit waits, relative locators, Actions API, BiDi logging/network, print page, file uploads, frames, alerts, cookies, virtual authenticator), based on the official documentation at https://www.selenium.dev/documentation/.

## Runnable scaffold

A ready-to-use project skeleton aligned with this skill lives at `assets/project-template/`. It is a working Python package that demonstrates `core / contracts / adapters / flows`, env-driven configuration, Selenium 4 with Selenium Manager, structured logging, dry-run mode, and example unit and integration tests. Copy it as the starting point of any new RPA.
