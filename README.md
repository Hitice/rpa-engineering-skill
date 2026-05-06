# RPA Engineering Skill (Selenium 4)

Build deterministic, testable, idempotent and auditable RPA using Selenium 4 — with enforced engineering standards.

---

## What this is

This project is an **engineering skill + reference architecture** for building RPA systems.

It is not:

* a framework
* a library
* a low-code tool

It is a **set of enforced rules and structure** designed to guide how automation is built.

It is intended to be used with AI coding assistants (Claude, Cursor, VSCode + extensions), while keeping full control over:

* architecture
* implementation decisions
* code quality

---

## What problem this solves

Most RPA implementations degrade over time due to:

* fragile synchronization (`time.sleep`)
* unstable selectors
* duplicated side effects
* lack of observability
* tight coupling between UI and business logic

This results in systems that are:

* hard to maintain
* hard to debug
* unsafe to re-run

This project enforces:

* deterministic synchronization (explicit waits)
* idempotent execution
* structured logging
* strict architectural boundaries

---

## Core concept (how to think)

Instead of writing automation directly:

```text
prompt → code → fragile automation
```

You operate through a controlled pipeline:

```text
SPEC → PLAN → ARCHITECTURE → BUILD → VERIFY → REVIEW
```

This pipeline is the core of the project.

It ensures that:

* requirements are explicit before implementation
* architecture is defined before code
* validation is mandatory

---

## Using with AI (Claude / Cursor / VSCode)

### Setup

```bash
mkdir -p .claude/skills
cp -r rpa-selenium-engineering .claude/skills/
```

Create:

```
.claude/system.md
```

```text
Load the skill "rpa-selenium-engineering".

Always follow:
SPEC → PLAN → ARCHITECTURE → BUILD → VERIFY → REVIEW

Do not generate code before SPEC.
```

---

### Day-to-day workflow

#### 1. Provide context

Example:

```text
Use rpa-selenium-engineering skill.

Automate submission and validation of records in a web portal.
```

---

#### 2. Validate SPEC

You review:

* inputs / outputs
* business rules
* failure cases

---

#### 3. Validate PLAN + ARCHITECTURE

You ensure:

* proper layer separation
* contracts are well defined
* no Selenium usage inside core

---

#### 4. Build

The agent generates:

* adapters
* page objects
* core services

---

#### 5. Verify (mandatory)

You confirm:

* unit tests exist
* dry-run works
* structured logs are generated

---

## Using in real scenarios

### New RPA

1. Copy the template
2. Define SPEC
3. Iterate through the pipeline
4. Validate at each stage

---

### Existing RPA (recommended approach)

Do not rewrite everything.

Refactor incrementally:

1. Wrap current automation in an adapter
2. Define contracts
3. extract business logic into `core/`
4. introduce state store (idempotency)
5. add structured logging
6. gradually remove sleeps and fragile selectors

---

## Architecture (practical view)

```
flows/      → orchestration
core/       → pure logic (no IO)
contracts/  → interfaces
adapters/   → Selenium / API / DB
```

Key rules:

* `core` has no external dependencies
* adapters handle all IO
* flows compose the use case

---

## What you get

* runnable Python template
* Selenium 4 with Selenium Manager
* Page Object pattern
* structured JSON logging
* SQLite state store
* retry mechanism
* dry-run mode
* unit and integration tests

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

## Example use case

Input:

```json
[
  { "key": "REC-001", "payload": {} }
]
```

Execution:

* login
* check existence
* submit if needed
* retry transient failures
* persist execution state

Output:

* structured logs per step
* artifacts on failure
* execution summary

---

## When NOT to use

* one-off scripts
* trivial automation
* stable API integrations
* desktop automation via coordinates
* CAPTCHA / 2FA flows
* mobile automation

---

## Engineering principles

* API-first
* no `time.sleep`
* no hardcoded values
* no global state
* idempotent operations
* structured logging per step

---

## License

MIT
