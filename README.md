# rpa-engineering-skill

Production-grade agent skill that teaches AI coding agents how to engineer **deterministic, testable, idempotent and auditable** RPA on top of **Selenium 4**.

This repo follows the open Agent Skills standard. Designed primarily for **Claude-powered IDEs** — Cursor and Claude Code — where the agent loads `SKILL.md` automatically and pulls the `references/` only when the current step needs them.

> **Selenium-first, API-first, human-out-of-the-loop. No `pyautogui`, no coordinate clicks, no `time.sleep`.**

## Why this exists

Most RPA code in the wild is:

- **flaky** — `sleep`-driven synchronization, absolute XPath copied from devtools
- **not testable** — business rules glued to the DOM, no seam for fakes
- **not idempotent** — every re-run produces duplicates at the destination
- **impossible to debug** — no structured logs, no correlation id, no artifacts on error
- **a closed source** — you cannot swap the browser for an API or run the logic in CI

This repo gives an AI coding agent the rules and the reference scaffold to **refuse those patterns from day one** and produce maintainable bots instead of single-use scripts.

## Selenium script vs traditional RPA vs this skill

| Approach                      | Determinism | Testability       | Idempotency       | Observability                     | Adapter swap |
|-------------------------------|:-----------:|:-----------------:|:-----------------:|:---------------------------------:|:------------:|
| Ad-hoc Selenium script        | ❌          | ❌                | ❌                | print statements                  | ❌           |
| UiPath / BluePrism / Power Automate | ⚠     | partial           | depends on author | vendor UI                         | ❌           |
| **rpa-engineering-skill**     | ✓           | unit + contract   | state machine     | JSON-per-step + `correlation_id` + `page_source` + screenshot on error | ✓ (Playwright, REST API) |

## Architecture at a glance

```
records (JSON / queue / DB)
        │
        ▼
   flows/        ─── filelock + state store + correlation_id (composition root)
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

A new adapter (Playwright, REST API, headless service) plugs in at the bottom and **requires zero changes** in `core/` or its tests.

## What's in this repo

```
rpa-selenium-engineering/        # the agent skill — copy this folder into your IDE
  SKILL.md                       # entry point: 6-phase pipeline, hard rules, red flags
  references/                    # loaded on demand by the agent
    architecture.md              # boundaries, idempotency, observability, retries
    selenium-utilities.md        # Selenium 4 cheatsheet (Manager, BiDi, EC, ...)
  assets/
    project-template/            # runnable Python scaffold (cp -r and start coding)
      pyproject.toml
      .env.example
      src/rpa_template/          # core / contracts / adapters / flows
      tests/                     # unit + contract + integration
      samples/                   # example records.json
LICENSE
README.md                        # this file
.gitignore
```

## Use it

The `rpa-selenium-engineering/` folder **is** the skill. Drop it into the directory your IDE/agent reads — that is the entire installation. Both flows below assume you cloned the repo first:

```bash
git clone https://github.com/Hitice/rpa-engineering-skill.git
cd rpa-engineering-skill
```

### Cursor

Copy (or symlink) the skill into your project's rules folder:

```powershell
# Windows / PowerShell
Copy-Item -Recurse rpa-selenium-engineering .cursor\rules\
```

```bash
# macOS / Linux
mkdir -p .cursor/rules
cp -r rpa-selenium-engineering .cursor/rules/
```

Cursor loads `SKILL.md` automatically on the next agent turn; the `references/` files are pulled in on demand.

### Claude Code

Install as a **personal** skill (available in every session, on your machine) or **project-scoped** (committed with the repo so the team gets it for free):

```bash
# Personal — ~/.claude/skills/
mkdir -p ~/.claude/skills
cp -r rpa-selenium-engineering ~/.claude/skills/

# Project — ./.claude/skills/ (commit it)
mkdir -p ./.claude/skills
cp -r rpa-selenium-engineering ./.claude/skills/
```

Verify the skill is registered with `claude /skills` — the entry should match the `name` / `description` from `SKILL.md`. The exact directory layout and command names follow the official Claude Code documentation: https://docs.claude.com/en/docs/claude-code/skills.

## Bootstrap a new RPA in seconds

```bash
cp -r rpa-selenium-engineering/assets/project-template my-rpa
cd my-rpa
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                       # fill RPA_TARGET_URL, RPA_USERNAME, RPA_PASSWORD
pytest                                     # unit tests run; integration auto-skips
rpa --records ./samples/records.json --dry-run
```

The template ships with a `BrowserPort` Protocol, a Selenium 4 adapter using **Selenium Manager** (no driver downloads), Page Objects, a JSON line structured logger, dry-run mode, idempotent submission and example tests.

## Concrete example: invoice submission to an ERP portal

A typical scenario you might describe to the agent — and what the scaffold actually does:

1. Input: `--records ./pending-invoices.json` (a list of `{key, payload}` items)
2. The flow acquires a `filelock` and refuses to start if another run holds it
3. Opens the SQLite state store; keys already in `SUCCESS` or `DEAD_LETTER` short-circuit the browser entirely
4. Boots Selenium 4 with **Selenium Manager** (no driver download), explicit waits, `data-testid` selectors centralized in Page Objects, `--headless=new`
5. Per record:
   - login → dashboard (Page Object)
   - `record_exists(invoice_number)`? → outcome `skipped`
   - else `submit(invoice)` → confirmation id → outcome `success`
   - on `IntegrationError` / `ElementTimeoutError`: `tenacity` retries with exponential backoff + jitter, every retry logged with attempt/error/delay; on exhaustion the cross-run state machine moves the item from `FAILED` → `DEAD_LETTER`
6. Each step emits one JSON record keyed by `correlation_id`; on error, `page_source` and a screenshot land under `artifacts/<correlation_id>/`
7. Run finishes with a summary record; exit codes: `0` ok, `1` errors, `2` dry-run inconclusive

The same flow runs as `--dry-run` against the real portal: it logs in, traverses every read-only step, **never submits**, **never persists state**, and reports each suppressed write as `status="skipped"` with `output_summary={"would_apply": true}`.

## Key principles enforced by the skill

- **API-first**: if a stable API exists, use it before the UI.
- **Deterministic synchronization**: only `WebDriverWait` + `expected_conditions`.
- **Externalized configuration**: every URL, credential, timeout, browser, headless flag, path and toggle comes from environment variables prefixed with `RPA_`.
- **Idempotency in two layers**: the destination is checked at runtime via the `BrowserPort`, and a `StateStore` (SQLite by default) keeps the per-key lifecycle across runs so terminal items are never re-attempted.
- **Resilient by construction**: `tenacity` retries transient failures intra-call, the state machine promotes exhausted items to `DEAD_LETTER` cross-run, and a `filelock`-based lock guarantees a single instance per host.
- **Layered architecture**: `core / contracts / adapters / flows`, no leakage of `WebDriver` into the core.
- **Structured observability**: one JSON record per step plus a run summary, all keyed by `correlation_id`.
- **Forbidden**: `pyautogui`, OCR-as-control, pixel coordinates, hardcoded driver paths, `time.sleep` for synchronization, silent `except`.

## When NOT to use

This skill is the wrong tool for:

- **Desktop automation by pixel coordinates, image recognition or keystroke replay.** Use the right OS-level tool — not Selenium.
- **One-off, throwaway scripts.** The engineering overhead (state store, contracts, structured logs) is justified only when the bot will run more than once or be inherited by someone else.
- **Tasks already covered by a stable API.** This skill *prefers* APIs over UI by hard rule; if there's a documented endpoint, do not drive a browser.
- **CAPTCHA solving, link spidering, performance testing, or 2FA-protected mailbox parsing.** The official Selenium guidance recommends against those, and so do we.
- **Mobile app automation.** Appium is a different ecosystem; the contracts and Page Objects here are web-shaped.

## Continuous integration

`.github/workflows/test.yml` runs on every push to `main` and on every pull request, against Python 3.11, 3.12 and 3.13: `ruff check`, `mypy --strict` over `src/`, and `pytest -m "not integration"` with coverage reporting.

## License

MIT — see [LICENSE](./LICENSE).
