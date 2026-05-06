"""Records Page Object: list and creation form."""

from __future__ import annotations

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from rpa_template.core.entities import Record
from rpa_template.exceptions import ElementTimeoutError


class RecordsPage:
    LIST = (By.CSS_SELECTOR, "[data-testid='records-list']")
    ADD_BUTTON = (By.CSS_SELECTOR, "[data-testid='add-record']")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "[data-testid='submit-record']")
    CONFIRMATION = (By.CSS_SELECTOR, "[data-testid='confirmation-id']")

    def __init__(
        self,
        driver: WebDriver,
        default_timeout_s: float,
        submit_timeout_s: float,
    ) -> None:
        self._driver = driver
        self._timeout = default_timeout_s
        self._submit_timeout = submit_timeout_s

    @staticmethod
    def _row_locator(key: str) -> tuple[str, str]:
        return (By.CSS_SELECTOR, f"[data-testid='record'][data-key='{key}']")

    @staticmethod
    def _field_locator(name: str) -> tuple[str, str]:
        return (By.CSS_SELECTOR, f"[data-testid='field-{name}']")

    def has_record(self, key: str) -> bool:
        try:
            WebDriverWait(self._driver, self._timeout).until(
                EC.presence_of_element_located(self.LIST)
            )
            self._driver.find_element(*self._row_locator(key))
            return True
        except NoSuchElementException:
            return False
        except TimeoutException as err:
            raise ElementTimeoutError("Records list did not load in time") from err

    def submit_record(self, record: Record) -> str:
        wait = WebDriverWait(self._driver, self._submit_timeout)
        try:
            wait.until(EC.element_to_be_clickable(self.ADD_BUTTON)).click()
            for field, value in record.payload.items():
                wait.until(
                    EC.visibility_of_element_located(self._field_locator(field))
                ).send_keys(str(value))
            wait.until(EC.element_to_be_clickable(self.SUBMIT_BUTTON)).click()
            confirmation_el = wait.until(EC.visibility_of_element_located(self.CONFIRMATION))
            return confirmation_el.text
        except TimeoutException as err:
            raise ElementTimeoutError(f"Submit failed for key={record.key}") from err
