# RPA Engineering (Selenium 4)

Build deterministic, testable, idempotent, and auditable web automation using Python and Selenium 4.

---

## What this is

This project is a production-grade RPA engineering template and standard.

It is designed for developers who want to build automation that:

* does not break randomly
* can be tested
* can be safely re-executed
* can be debugged in production

This is not a script generator.
This is a structured way to engineer automation systems.

---

## Why this exists

Most RPA code in the wild has the same problems:

* Flaky synchronization

  * `time.sleep`, copied XPath, race conditions

* No testability

  * business logic tied to DOM
  * impossible to mock or validate

* Not idempotent

  * reruns create duplicates or corrupt state

* Impossible to debug

  * no structured logs
  * no correlation id
  * no artifacts on failure

* Vendor lock-in

  * cannot replace UI with API
  * cannot run in CI

This project eliminates those problems by design.

---

## Core principles

### API-first

If an API exists, use it before UI automation.

---

### Deterministic execution

* Explicit waits only (`WebDriverWait`)
* No `sleep`
* Domain-based conditions

---

### Idempotency by design

* Safe to re-run
* No duplicate side effects
* State tracked across executions

---

### Layered architecture

```
flows/      → orchestration
core/       → pure logic (no IO)
contracts/  → interfaces
adapters/   → Selenium / DB / API
```

* `core` has zero external dependencies
* adapters are swappable (Selenium → API → Playwright)

---

### Observability

Every step produces structured logs:

```json
{
  "correlation_id": "...",
  "step": "submit_invoice",
  "status": "success",
  "duration_ms": 1200
}
```

On failure:

* screenshot
* page source
* full context

---

## What you get

* Runnable Python project template
* Selenium 4 setup with Selenium Manager
* Page Object pattern
* Structured JSON logging
* SQLite state store (idempotency)
* Retry system (tenacity)
* Dry-run mode
* Unit + integration tests
* CI ready (ruff, mypy, pytest)

---

## Architecture overview

```
records (JSON / queue / DB)
        ↓
flows/ (entrypoint + orchestration)
        ↓
core/ (pure business logic)
        ↓
contracts/ (interfaces)
        ↓
adapters/ (Selenium / API / DB)
        ↓
external systems
```

Adapters can be replaced without changing core logic.

---

## Quick start

```bash
git clone https://github.com/Hitice/rpa-engineering-skill.git
cd rpa-engineering-skill

cp -r rpa-selenium-engineering/assets/project-template my-rpa
cd my-rpa

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

cp .env.example .env
# configure:
# RPA_TARGET_URL
# RPA_USERNAME
# RPA_PASSWORD

pytest

rpa --records ./samples/records.json --dry-run
```

---

## Real example

### Use case: invoice submission

Input:

```json
[
  { "key": "INV-001", "payload": {} }
]
```

Execution:

* login to portal
* check if invoice already exists
* submit only if missing
* retry on transient failure
* store result in state

Output:

* structured logs per step
* artifacts on failure
* summary report

---

## Comparison

| Approach                 | Determinism | Testability | Idempotency | Observability   | Flexibility |
| ------------------------ | ----------- | ----------- | ----------- | --------------- | ----------- |
| Selenium scripts         | ❌           | ❌           | ❌           | print logs      | ❌           |
| RPA tools (UiPath, etc.) | ⚠           | limited     | depends     | UI-based        | ❌           |
| This project             | ✔           | ✔           | ✔           | structured logs | ✔           |

---

## When NOT to use

Do not use this project for:

* one-off scripts
* simple automation tasks
* cases where a stable API already exists
* desktop automation via coordinates
* CAPTCHA / 2FA flows
* mobile automation (use Appium)

---

## Optional: AI agent usage

This project follows the Agent Skills format and can be used with tools like Cursor or Claude Code.

However, it is fully usable without any AI tooling.

---

## License

MIT
