# rpa-engineering-skill

Build production-grade browser automation in Python — deterministic, idempotent, testable, and observable by default.

## What This Project Is

`rpa-engineering-skill` is an opinionated set of engineering conventions and a runnable Python scaffold for browser-driven automation on top of Selenium 4.

It gives you:

- a layered project structure (`core` / `contracts` / `adapters` / `flows`)
- a state machine that prevents duplicate work across runs
- structured JSON logging with end-to-end `correlation_id`
- typed retries with jitter for transient failures
- a `--dry-run` mode that exercises the real target without writes
- a CI workflow with lint, type checks, unit and contract tests

It is intended for backend engineers, automation engineers, and tech leads who need bots that survive contact with real portals — not throwaway scripts.

## Why This Exists

Most RPA code in the wild fails the same way:

- **Flaky synchronization** — `time.sleep` everywhere, absolute XPath copied from devtools.
- **Not testable** — business logic glued to the DOM, no seam for fakes.
- **Not idempotent** — re-running creates duplicate records at the destination.
- **Hard to debug** — print statements, no correlation between steps, no artifacts on failure.
- **Vendor lock-in** — UiPath, BluePrism and similar tools couple your logic to a proprietary runtime; you cannot run it in CI or swap the browser for an API.

This project encodes the engineering decisions that fix those problems, and ships a working scaffold that demonstrates each one.

## Key Principles

**API-first.** If a stable API exists for the task, use it. Browsers are the integration surface of last resort.

**Deterministic execution.** Synchronization is `WebDriverWait` + `expected_conditions` only. No `time.sleep`. No magic timeouts. No coordinate clicks.

**Idempotency in two layers.**

- The destination is checked at runtime through the `BrowserPort` (eventual consistency is tolerated).
- A `StateStore` (SQLite by default) tracks the per-key lifecycle across runs. Terminal items (`SUCCESS`, `DEAD_LETTER`) never re-touch the UI.

**Layered architecture.**

- `core/` is import-pure: standard library + `pydantic` value objects only.
- `contracts/` defines the seams (`BrowserPort`, `StateStore`, `StructuredLogger`).
- `adapters/` owns all IO (Selenium 4, SQLite, JSON-line logger, `tenacity`).
- `flows/` is the only composition root: acquires the lock, builds adapters, runs the processor.

A new adapter (Playwright, REST API) plugs in at the bottom and requires zero changes in `core/`.

**Externalized configuration.** Every URL, credential, timeout, browser, headless flag and path comes from environment variables prefixed with `RPA_`, validated by `pydantic-settings`. Secrets are typed `SecretStr`.

**Observability by default.** One JSON record per step, plus a run summary, all keyed by `correlation_id`. On error, `page_source` and a screenshot are persisted under `artifacts/<correlation_id>/`. Sensitive payload keys are redacted by a configurable list.

## Architecture Overview

```
records (JSON / queue / DB)
        │
        ▼
   flows/        ─── filelock + state store + correlation_id  (composition root)
        │
        ▼ injects via contracts
   core/         ─── pure orchestration, no IO, no Selenium
        │
        ▼ talks through Protocols
   contracts/    ─── BrowserPort  ·  StateStore  ·  StructuredLogger
        │
        ▼ implemented by
   adapters/     ─── Selenium 4  ·  SQLite  ·  JSON-line logger  ·  tenacity retry
        │
        ▼
   external system (browser  ·  filesystem  ·  database)
```

State machine for each record:

```
PENDING ─▶ IN_PROGRESS ─▶ SUCCESS                          (terminal)
                       ─▶ FAILED ─▶ ... ─▶ DEAD_LETTER     (terminal at max_attempts)
                       ─▶ SKIPPED                           (non-terminal: re-validated each run)
```

## What You Get

The runnable scaffold under `rpa-selenium-engineering/assets/project-template/` includes:

- **`BrowserPort`**, **`StateStore`**, **`StructuredLogger`** Protocols.
- **`SeleniumBrowserAdapter`** with Selenium Manager (no driver downloads), W3C `Options`, Page Object Models, `data-testid`-first selectors. Captures `page_source` + screenshot on every domain error.
- **`SqliteStateStore`** with WAL mode for file-backed databases, plus a `NullStateStore` fallback when persistence is intentionally disabled.
- **`JsonStructuredLogger`** with case-insensitive substring redaction, recursive into nested dicts and lists.
- **`tenacity` retry policy** with exponential backoff, random jitter, and a `before_sleep` hook that surfaces attempt/error/delay through the logger.
- **`filelock`** single-instance enforcement at the flow layer, with bounded timeout.
- **Tests:** unit (core), contract (parametrized over `StateStore` implementations), integration (opt-in, marked).
- **Tooling:** `pyproject.toml` with `ruff`, `mypy --strict`, `pytest`, coverage.
- **CI:** GitHub Actions workflow against Python 3.11, 3.12 and 3.13.

The reference documents (`SKILL.md`, `references/architecture.md`, `references/selenium-utilities.md`) are the rationale and the cheatsheet — read them when you need the why behind a rule.

## Quick Start

Clone and bootstrap a new project from the template:

```bash
git clone https://github.com/Hitice/rpa-engineering-skill.git
cd rpa-engineering-skill
cp -r rpa-selenium-engineering/assets/project-template my-rpa
cd my-rpa

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Configure the environment:

```bash
cp .env.example .env
# Fill at minimum: RPA_TARGET_URL, RPA_USERNAME, RPA_PASSWORD
```

Run the test suite (unit + contract; integration auto-skips without a live target):

```bash
pytest
```

Exercise the flow against the real target without writes:

```bash
rpa --records ./samples/records.json --dry-run
```

Run for real:

```bash
rpa --records ./samples/records.json
```

Exit codes: `0` ok, `1` errors, `2` dry-run inconclusive (empty input).

## Real Example: Invoice Submission to an ERP Portal

**Input** — `pending-invoices.json`:

```json
[
  { "key": "INV-2026-0001", "payload": { "amount": "150.00", "vendor": "Acme" } },
  { "key": "INV-2026-0002", "payload": { "amount": "275.50", "vendor": "Globex" } }
]
```

**Behavior**:

1. The flow acquires a `filelock` and refuses to start if another run holds it.
2. Opens the SQLite state store. Keys already in `SUCCESS` or `DEAD_LETTER` short-circuit — no browser traffic.
3. Boots Selenium 4 via Selenium Manager (no driver downloads), `--headless=new`, explicit waits, `data-testid` selectors centralized in Page Objects.
4. For each record:
   - Login → dashboard (Page Object).
   - `record_exists(key)`? → `skipped` (re-validated every run; the destination is the source of truth).
   - Otherwise `submit(record)` → confirmation id → `success`.
5. On `IntegrationError` / `ElementTimeoutError`: retries with exponential backoff + jitter, every attempt logged. On exhaustion the state machine moves the item from `FAILED` → `DEAD_LETTER`.
6. On any error, `page_source` + screenshot are persisted to `artifacts/<correlation_id>/`.

**Output** — one JSON record per step plus a run summary, on stdout:

```json
{"timestamp":"2026-05-06T10:00:01Z","process":"invoice-bot","correlation_id":"a1b2-...","step":"process_record","status":"success","duration_ms":1842.5,"attempt":1,"input_summary":{"key":"INV-2026-0001"},"output_summary":{"confirmation_id":"ERP-9981"}}
{"timestamp":"2026-05-06T10:00:03Z","process":"invoice-bot","correlation_id":"a1b2-...","step":"_run_summary","status":"success","duration_ms":2734.1,"totals":{"success":2}}
```

The same flow runs as `--dry-run` against the real portal: it logs in, traverses every read-only step, never submits, never persists state, and reports each suppressed write as `status="skipped"` with `output_summary={"would_apply": true}`.

## Comparison

| Aspect             | Ad-hoc Selenium script | UiPath / BluePrism / Power Automate | rpa-engineering-skill |
|--------------------|------------------------|--------------------------------------|------------------------|
| Synchronization    | `time.sleep`           | proprietary activities               | `WebDriverWait` + `expected_conditions` only |
| Testability        | none                   | partial (vendor harness)             | unit + contract + integration with fakes |
| Idempotency        | manual or absent       | depends on the author                | enforced by `StateStore` + state machine |
| Retry strategy     | retry by restart       | proprietary block                    | typed `tenacity` policy with jitter and telemetry |
| Observability      | print / ad-hoc logs    | vendor UI                            | one JSON record per step + `correlation_id` + page_source/screenshot on error |
| Configuration      | hardcoded              | vendor settings                      | env-driven, validated by `pydantic-settings` |
| CI / version control| difficult             | proprietary export                   | `pyproject.toml`, `pytest`, `ruff`, `mypy --strict` |
| Vendor lock-in     | none                   | high                                 | none — pure Python, swap the adapter |

## When NOT to Use

This project is the wrong tool for:

- **Desktop automation** by pixel coordinates, image recognition or keystroke replay. Selenium is not for desktop apps; use the right OS-level tool.
- **One-off, throwaway scripts.** The state store, contracts and structured logs are overkill when the bot will run once and be deleted.
- **Tasks already covered by a stable API.** The hard rule is API-first; if there's a documented endpoint, do not drive a browser.
- **CAPTCHA solving, link spidering, performance testing, 2FA-protected mailbox parsing.** The official Selenium guidance recommends against those.
- **Mobile app automation.** Appium is a different ecosystem; the contracts here are web-shaped.

## Continuous Integration

`.github/workflows/test.yml` runs on every push to `main` and on every pull request, against Python 3.11, 3.12 and 3.13:

- `ruff check` (E, F, I, B, UP, SIM, RUF)
- `mypy --strict` over `src/`
- `pytest -m "not integration"` with coverage

Integration tests are opt-in: set `RPA_TARGET_URL`, `RPA_USERNAME`, `RPA_PASSWORD` and unmark `-m "not integration"` to run them.

## Optional: Use With AI Coding Agents

The repo also ships `rpa-selenium-engineering/` as an [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills), so AI coding agents pick up these conventions automatically:

- **Cursor** — copy `rpa-selenium-engineering/` into `.cursor/rules/` of your project.
- **Claude Code** — copy into `~/.claude/skills/` (personal) or `./.claude/skills/` (project, committed).

The conventions and scaffold work standalone; this is a convenience for teams already using one.

## License

MIT — see [LICENSE](./LICENSE).
