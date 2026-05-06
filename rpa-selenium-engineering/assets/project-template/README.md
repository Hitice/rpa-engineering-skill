# RPA Template (Selenium-first)

Runnable scaffold aligned with the `rpa-selenium-engineering` agent skill. Demonstrates `core / contracts / adapters / flows` separation, env-driven configuration, Selenium 4 with Selenium Manager, structured logging and dry-run.

## Layout

```
src/rpa_template/
  config.py             # pydantic-settings, all values from env
  exceptions.py         # domain errors
  cli.py                # entry point (rpa command)
  contracts/            # Protocols (BrowserPort, StructuredLogger)
  core/                 # pure business logic, no IO, no Selenium
  adapters/             # Selenium 4, Page Objects, JSON logger
  flows/                # orchestration
tests/
  unit/                 # core only, no browser
  integration/          # adapters, marked integration, opt-in
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                # then fill RPA_TARGET_URL, RPA_USERNAME, RPA_PASSWORD
pytest                              # runs unit tests; integration tests are skipped without env
rpa --records ./samples/records.json --dry-run
```

Selenium 4 ships with Selenium Manager, so no driver download is needed; the bundled `webdriver.Chrome()` resolves the binary automatically.

## Conventions

- No `time.sleep`. Synchronization uses `WebDriverWait` plus `expected_conditions`.
- No hardcoded values. URLs, credentials, browser, headless mode, timeouts and paths come from environment variables prefixed with `RPA_`.
- No `pyautogui` or coordinate-based input.
- Selectors live inside Page Objects, prefer `data-testid`.
- Domain errors only at module boundaries; framework exceptions are caught and translated.

## Extending

To add a new use case:

1. Define entities in `core/entities.py`.
2. Add a service in `core/services.py` that depends only on contracts.
3. Add a `BrowserPort` method in `contracts/browser.py` if a new browser intent is needed.
4. Implement it in `adapters/selenium_browser.py`, with selectors in a new Page Object under `adapters/pages/`.
5. Wire the use case in `flows/`.
6. Add unit tests against a fake adapter and an integration test marked `integration`.

See the parent skill `rpa-selenium-engineering/SKILL.md` for the full pipeline.
