# Selenium 4 Utilities (Python)

Curated reference of Selenium 4 features that this skill prefers, based on the official documentation at https://www.selenium.dev/documentation/. Use this file to pick the right tool for each step instead of reinventing it.

## Driver bootstrap with Selenium Manager

Selenium 4 ships with **Selenium Manager**, a Rust-based CLI integrated into the bindings. It auto-resolves the correct browser driver, so projects must not hardcode driver paths.

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

options = ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)
```

Cross-browser pattern (browser name is read from configuration):

```python
def build_driver(browser: str, headless: bool):
    if browser == "chrome":
        from selenium.webdriver.chrome.options import Options
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        return webdriver.Chrome(options=opts)
    if browser == "firefox":
        from selenium.webdriver.firefox.options import Options
        opts = Options()
        if headless:
            opts.add_argument("-headless")
        return webdriver.Firefox(options=opts)
    if browser == "edge":
        from selenium.webdriver.edge.options import Options
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        return webdriver.Edge(options=opts)
    raise ValueError(f"Unsupported browser: {browser}")
```

## Explicit waits with expected_conditions

Always synchronize on a domain-meaningful condition, never on time.

```python
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WebDriverWait(driver, timeout).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='submit']"))
).click()
```

Useful conditions:

- `presence_of_element_located` — DOM only
- `visibility_of_element_located` — visible to user
- `element_to_be_clickable` — visible and enabled
- `text_to_be_present_in_element`
- `staleness_of` — wait for a previous element to detach
- `url_contains`, `url_to_be`, `url_matches`
- `number_of_windows_to_be`
- `frame_to_be_available_and_switch_to_it`
- `alert_is_present`
- `invisibility_of_element_located` — for spinners

Custom predicate when needed:

```python
def row_count_at_least(locator, n):
    def _predicate(driver):
        return len(driver.find_elements(*locator)) >= n
    return _predicate

WebDriverWait(driver, timeout).until(row_count_at_least((By.CSS_SELECTOR, "tr"), 10))
```

## Locator strategy

Preference order:

1. `data-testid` — `(By.CSS_SELECTOR, "[data-testid='login-submit']")`
2. Stable `id`
3. ARIA — `(By.CSS_SELECTOR, "[role='button'][aria-label='Save']")`
4. Stable CSS class with semantic meaning
5. Relative locators (Selenium 4)
6. As a last resort, a short, attribute-based XPath

### Relative locators

```python
from selenium.webdriver.support.relative_locator import locate_with

password = driver.find_element(
    locate_with(By.TAG_NAME, "input").below({By.ID: "username"})
)
```

Available helpers: `above`, `below`, `to_left_of`, `to_right_of`, `near`.

## Actions API

Use for keyboard-mouse sequences without coordinates against the OS.

```python
from selenium.webdriver import ActionChains, Keys

ActionChains(driver) \
    .move_to_element(menu) \
    .pause(0)  \
    .click(submenu) \
    .send_keys(Keys.ENTER) \
    .perform()
```

Sub-APIs: keyboard, mouse, pen, wheel. Prefer this over any OS-level input library.

## File upload

Always drive the actual `<input type="file">`. Never simulate a system file chooser.

```python
driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(absolute_path)
```

For grids and remote nodes, set the local file detector when needed.

## Frames and windows

```python
driver.switch_to.frame(driver.find_element(By.NAME, "content"))
driver.switch_to.default_content()

driver.switch_to.new_window("tab")
driver.switch_to.window(driver.window_handles[0])
```

## Alerts and cookies

```python
WebDriverWait(driver, timeout).until(EC.alert_is_present()).accept()

driver.add_cookie({"name": "session", "value": token, "secure": True})
```

## Print page

Selenium 4 supports printing the current page to PDF directly through the driver, useful for invoices, receipts and audit trails:

```python
from selenium.webdriver.common.print_page_options import PrintOptions

options = PrintOptions()
options.page_ranges = ["1-2"]
pdf_b64 = driver.print_page(options)
```

Decode `pdf_b64` and write it to the artifact folder under the run's `correlation_id`.

## Network and logs via BiDi (W3C)

Selenium 4 exposes the W3C BiDi protocol. Use it to capture network traffic, console logs and JavaScript errors instead of polling DOM. The Python BiDi surface evolves between minor releases; pin a Selenium version and verify the exact API against the official docs at https://www.selenium.dev/documentation/webdriver/bidirectional/bidi_api/ before relying on it.

Conceptual sketch (Selenium >= 4.20):

```python
def on_console_message(message):
    # message has level, text, args, stack_trace, etc.
    if message.level == "error":
        raise AssertionError(f"console error: {message.text}")

driver.script.add_console_message_handler(on_console_message)
```

Patterns enabled by BiDi:

- assert that no `error` console entry was produced during a critical step
- intercept and assert calls to a backend endpoint to confirm a submit actually happened (`driver.network.add_request_handler(...)`)
- block known-bad third-party domains during automation runs

## Virtual Authenticator

For WebAuthn-protected portals, register a virtual authenticator instead of automating a hardware key.

```python
from selenium.webdriver.common.virtual_authenticator import VirtualAuthenticatorOptions

options = VirtualAuthenticatorOptions()
authenticator_id = driver.add_virtual_authenticator(options)
```

## Driver lifecycle

- one driver per use case execution
- always `driver.quit()` in a `finally`, even on exceptions
- prefer fresh sessions per logical run; do not share a driver across unrelated flows
- pass driver capabilities through `Options`, never via deprecated `DesiredCapabilities`

## Test practices encouraged by the project

From the official documentation:

- Page Object Models for selector and intention encapsulation
- domain-specific language at the test level
- generate application state via API, not via UI
- mock external services
- a fresh browser per test
- avoid sharing state across tests
- avoid CAPTCHAs, link spidering, performance testing and 2FA-protected mailboxes via Selenium

## Anti-patterns to refuse

- `time.sleep` for synchronization
- absolute or positional XPath copied from devtools
- driver paths hardcoded; always rely on Selenium Manager
- using OS-level keyboard/mouse libraries to control the browser
- swallowing `WebDriverException` and continuing
- hardcoded URLs, credentials and timeouts
