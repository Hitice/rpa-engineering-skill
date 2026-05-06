# rpa-selenium-engineering

Production-grade agent skill that teaches AI coding agents how to engineer **deterministic, testable, idempotent and auditable** RPA on top of **Selenium 4**.

This repo follows the open Agent Skills standard, so the same `SKILL.md` works in Claude.ai, Claude Code, Cursor, Gemini CLI, Windsurf and any agent that consumes Markdown skills.

> **Selenium-first, API-first, human-out-of-the-loop. No `pyautogui`, no coordinate clicks, no `time.sleep`.**

## What's in this repo

```
rpa-selenium-engineering/        # the agent skill (kebab-case folder)
  SKILL.md                       # entry point with the 6-phase pipeline
  references/
    architecture.md              # boundaries, idempotency, observability, retries
    selenium-utilities.md        # Selenium 4 features cheatsheet (Manager, BiDi, EC, etc.)
  assets/
    project-template/            # runnable Python scaffold
      pyproject.toml
      .env.example
      src/rpa_template/          # core / contracts / adapters / flows
      tests/                     # unit + integration
      samples/                   # example records.json
LICENSE
README.md                        # this file
.gitignore
```

## Use it

### Cursor

Copy `rpa-selenium-engineering/SKILL.md` (and optionally the `references/` folder) into `.cursor/rules/` of your project, or reference the whole skill directory.

### Claude Code

```bash
git clone <this-repo>
claude --plugin-dir ./rpa-selenium-engineering
```

### Claude.ai

Zip the `rpa-selenium-engineering/` folder and upload it under **Settings ▸ Capabilities ▸ Skills**.

### Any other agent

Skills are plain Markdown. Drop `SKILL.md` into your agent's instruction surface (system prompt, rules file, AGENTS.md) and the references will be discovered on demand.

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

## Key principles enforced by the skill

- **API-first**: if a stable API exists, use it before the UI.
- **Deterministic synchronization**: only `WebDriverWait` + `expected_conditions`.
- **Externalized configuration**: every URL, credential, timeout, browser, headless flag, path and toggle comes from environment variables prefixed with `RPA_`.
- **Idempotency in two layers**: the destination is checked at runtime via the `BrowserPort`, and a `StateStore` (SQLite by default) keeps the per-key lifecycle across runs so terminal items are never re-attempted.
- **Resilient by construction**: `tenacity` retries transient failures intra-call, the state machine promotes exhausted items to `DEAD_LETTER` cross-run, and a `filelock`-based lock guarantees a single instance per host.
- **Layered architecture**: `core / contracts / adapters / flows`, no leakage of `WebDriver` into the core.
- **Structured observability**: one JSON record per step plus a run summary, all keyed by `correlation_id`.
- **Forbidden**: `pyautogui`, OCR-as-control, pixel coordinates, hardcoded driver paths, `time.sleep` for synchronization, silent `except`.

## Continuous integration

`.github/workflows/test.yml` runs on every push to `main` and on every pull request, against Python 3.11, 3.12 and 3.13: `ruff check`, `mypy --strict` over `src/`, and `pytest -m "not integration"` with coverage reporting.

## License

MIT — see [LICENSE](./LICENSE).
