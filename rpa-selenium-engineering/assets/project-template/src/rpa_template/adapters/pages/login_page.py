"""Login Page Object.

Selectors are centralized as class attributes. Prefer ``data-testid`` so the
automation does not depend on visual layout or copy changes.
"""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class LoginPage:
    USERNAME = (By.CSS_SELECTOR, "[data-testid='username']")
    PASSWORD = (By.CSS_SELECTOR, "[data-testid='password']")
    SUBMIT = (By.CSS_SELECTOR, "[data-testid='login-submit']")
    DASHBOARD = (By.CSS_SELECTOR, "[data-testid='dashboard']")

    def __init__(self, driver: WebDriver, default_timeout_s: float) -> None:
        self._driver = driver
        self._timeout = default_timeout_s

    def login(self, username: str, password: str) -> None:
        wait = WebDriverWait(self._driver, self._timeout)
        wait.until(EC.visibility_of_element_located(self.USERNAME)).send_keys(username)
        self._driver.find_element(*self.PASSWORD).send_keys(password)
        wait.until(EC.element_to_be_clickable(self.SUBMIT)).click()
        wait.until(EC.visibility_of_element_located(self.DASHBOARD))
