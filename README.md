# RPA Engineering Skill (Selenium 4)

Build deterministic, testable, idempotent, and auditable RPA using Selenium 4 — with enforced engineering standards.

---

## What this is

This project is an **engineering skill + reference architecture** for building RPA systems.

It is designed to be used with AI coding assistants (Claude, Cursor, etc.), while maintaining full control over:

* architecture
* decisions
* code quality

It enforces **how automation must be engineered**.

---

## Core idea

Instead of writing RPA directly:

```text
prompt → code → fragile automation
```

You operate through a controlled pipeline:

```text
SPEC → PLAN → ARCHITECTURE → BUILD → VERIFY → REVIEW
```

This replaces traditional RPA documentation and aligns implementation with design.

---

## Replacing PDD / SDD

Traditional RPA:

```text
PDD → SDD → implementation
```

Problems:

* documents become outdated
* divergence from code

---

This project:

```text
SPEC → PLAN → ARCHITECTURE → BUILD
```

Mapping:

| Traditional | This project        |
| ----------- | ------------------- |
| PDD         | SPEC                |
| SDD         | PLAN + ARCHITECTURE |

Result:

* no drift between documentation and code
* specification becomes executable

---

## Usage with Claude + VSCode (primary workflow)

This is the **intended way to use the project**.

---

### Setup

```bash
mkdir -p .claude/skills
cp -r rpa-selenium-engineering .claude/skills/
```

Create:

```bash
.claude/system.md
```

```text
Load the skill "rpa-selenium-engineering".

Always follow:
SPEC → PLAN → ARCHITECTURE → BUILD → VERIFY → REVIEW

Do not generate code before SPEC.
```

---

### How to use (day-to-day)

#### 1. Start with context

```text
Use rpa-selenium-engineering skill.

Automate invoice submission in SAP Fiori.
```

---

#### 2. Validate SPEC

Check:

* inputs / outputs
* rules
* failure cases

---

#### 3. Validate PLAN + ARCHITECTURE

Ensure:

* correct separation of layers
* contracts defined
* no Selenium leaking into core

---

#### 4. Build

Generate:

* adapters
* page objects
* core services

---

#### 5. Verify (mandatory)

Ensure:

* unit tests exist
* dry-run works
* structured logs

---

## What problem this solves

Most RPA implementations fail due to:

* `time.sleep` synchronization
* fragile selectors
* no testability
* duplicate side effects
* no observability

This project enforces:

* explicit waits
* idempotency
* structured logging
* layered architecture

---

## Architecture overview

```text
flows/      → orchestration
core/       → pure logic (no IO)
contracts/  → interfaces
adapters/   → Selenium / API / DB
```

Rules:

* `core` has zero external dependencies
* adapters contain all IO
* flows compose everything

---

## What you get

* Runnable Python template
* Selenium 4 with Selenium Manager
* Page Objects
* Structured JSON logs
* SQLite state store
* Retry system
* Dry-run mode
* Unit + integration tests

---

## Starting a new project

```bash
cp -r rpa-selenium-engineering/assets/project-template my-rpa
cd my-rpa

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

cp .env.example .env
pytest
rpa --records ./samples/records.json --dry-run
```

---

## Improving an existing RPA (recommended approach)

Do not rewrite everything.

Apply incrementally:

### Step 1 — Wrap existing automation

```text
adapters/legacy_adapter.py
```

---

### Step 2 — Define contracts

```text
contracts/
```

---

### Step 3 — Move business logic

```text
core/
```

---

### Step 4 — Add idempotency

```text
state_store (SQLite)
```

---

### Step 5 — Add structured logging

```text
correlation_id + step logs
```

---

### Step 6 — Refactor Selenium gradually

* remove sleeps
* improve selectors
* add waits

---

## Example use case

Invoice submission:

Input:

```json
[
  { "key": "INV-001", "payload": {} }
]
```

Execution:

* login
* check existence
* submit if needed
* retry failures
* persist state

Output:

* structured logs
* artifacts on failure
* summary

---

## Comparison

| Approach         | Determinism | Testability | Idempotency | Observability |
| ---------------- | ----------- | ----------- | ----------- | ------------- |
| Selenium scripts | ❌           | ❌           | ❌           | ❌             |
| RPA tools        | ⚠           | partial     | depends     | limited       |
| This project     | ✔           | ✔           | ✔           | ✔             |

---

## When NOT to use

* one-off scripts
* trivial automation
* stable API already available
* desktop automation (coordinates)
* CAPTCHA / 2FA
* mobile automation

---

## Design principles

* API-first
* no `time.sleep`
* no hardcoded values
* no global state
* idempotent operations
* structured logs per step

---

## License

MIT
