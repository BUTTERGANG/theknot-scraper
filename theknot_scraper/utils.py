"""
Utility functions for web scraping with anti-detection measures
"""
import time
import random
import pickle
import json
from pathlib import Path
from typing import Optional, List, Tuple
from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """
    Sleep for a random amount of time to simulate human behavior

    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Waiting {delay:.2f} seconds")
    time.sleep(delay)


def human_type(element, text: str, min_delay: float = 0.1, max_delay: float = 0.3) -> None:
    """
    Type text with random delays between keystrokes to simulate human typing

    Args:
        element: Selenium WebElement
        text: Text to type
        min_delay: Minimum delay between keystrokes
        max_delay: Maximum delay between keystrokes
    """
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))


def smooth_scroll(driver: WebDriver, scroll_pause: float = 0.5, num_scrolls: int = 3) -> None:
    """
    Scroll down the page smoothly in multiple steps

    Args:
        driver: Selenium WebDriver instance
        scroll_pause: Pause between scroll actions
        num_scrolls: Number of scroll actions
    """
    logger.debug(f"Scrolling page in {num_scrolls} steps")

    # Get total page height
    total_height = driver.execute_script("return document.body.scrollHeight")
    current_position = 0

    for i in range(num_scrolls):
        # Random scroll amount
        scroll_by = random.randint(300, 600)
        current_position += scroll_by

        # Don't scroll past the bottom
        if current_position > total_height:
            current_position = total_height

        # Smooth scroll using JavaScript
        driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
        time.sleep(scroll_pause)

        # Random chance to scroll back up slightly (like humans do)
        if random.random() < 0.2:
            scroll_back = random.randint(50, 150)
            driver.execute_script(f"window.scrollBy({{top: -{scroll_back}, behavior: 'smooth'}});")
            time.sleep(scroll_pause * 0.5)


def move_mouse_randomly(driver: WebDriver, num_moves: int = 3) -> None:
    """
    Move mouse to random positions on the page

    Args:
        driver: Selenium WebDriver instance
        num_moves: Number of random mouse movements
    """
    logger.debug(f"Simulating {num_moves} random mouse movements")

    actions = ActionChains(driver)

    for _ in range(num_moves):
        # Random coordinates within viewport
        x_offset = random.randint(100, 800)
        y_offset = random.randint(100, 600)

        # Move to random position with some randomness in the path
        try:
            actions.move_by_offset(x_offset, y_offset).perform()
            time.sleep(random.uniform(0.1, 0.3))

            # Reset position
            actions.move_by_offset(-x_offset, -y_offset).perform()
        except Exception as e:
            logger.debug(f"Mouse movement error (expected): {e}")
            # Reset ActionChains if it fails
            actions = ActionChains(driver)


def simulate_human_behavior(driver: WebDriver, config) -> None:
    """
    Combine multiple human behavior simulations

    Args:
        driver: Selenium WebDriver instance
        config: ScraperConfig instance
    """
    logger.debug("Simulating human behavior")

    # Random initial delay
    random_delay(1, 2)

    # Random scrolling
    if config.enable_random_scrolling:
        smooth_scroll(driver, config.scroll_pause, num_scrolls=random.randint(2, 4))

    # Random mouse movements
    if config.enable_mouse_movement:
        move_mouse_randomly(driver, num_moves=random.randint(2, 5))

    # Scroll back to top
    driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
    random_delay(0.5, 1)


def safe_find_element(driver: WebDriver, selectors: List[str], by: By = By.CSS_SELECTOR,
                      timeout: int = 20) -> Optional:
    """
    Try multiple selectors to find an element

    Args:
        driver: Selenium WebDriver instance
        selectors: List of CSS selectors or XPath expressions
        by: Selenium By locator type
        timeout: Wait timeout in seconds

    Returns:
        WebElement if found, None otherwise
    """
    for selector in selectors:
        try:
            logger.debug(f"Trying selector: {selector}")
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            logger.debug(f"Found element with selector: {selector}")
            return element
        except TimeoutException:
            continue
        except Exception as e:
            logger.debug(f"Error with selector {selector}: {e}")
            continue

    logger.warning(f"Could not find element with any of the provided selectors")
    return None


def safe_find_elements(driver: WebDriver, selectors: List[str], by: By = By.CSS_SELECTOR,
                       timeout: int = 20) -> List:
    """
    Try multiple selectors to find elements

    Args:
        driver: Selenium WebDriver instance
        selectors: List of CSS selectors or XPath expressions
        by: Selenium By locator type
        timeout: Wait timeout in seconds

    Returns:
        List of WebElements (empty if none found)
    """
    for selector in selectors:
        try:
            logger.debug(f"Trying selector: {selector}")
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            elements = driver.find_elements(by, selector)
            if elements:
                logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                return elements
        except TimeoutException:
            continue
        except Exception as e:
            logger.debug(f"Error with selector {selector}: {e}")
            continue

    logger.warning(f"Could not find elements with any of the provided selectors")
    return []


def extract_text(element) -> str:
    """
    Safely extract text from an element

    Args:
        element: Selenium WebElement

    Returns:
        Extracted text or empty string
    """
    if element is None:
        return ""

    try:
        # Check if it's a meta tag with content attribute
        tag_name = element.tag_name.lower()
        if tag_name == "meta":
            content = element.get_attribute("content")
            if content:
                return content.strip()

        # Try standard text extraction
        text = element.text.strip()
        if text:
            return text

        # Try alternative methods if .text is empty
        text = element.get_attribute("textContent").strip()
        if text:
            return text

        text = element.get_attribute("innerText").strip()
        if text:
            return text

        # For other elements with content attribute
        content = element.get_attribute("content")
        if content:
            return content.strip()

        return ""
    except Exception as e:
        logger.debug(f"Error extracting text: {e}")
        return ""


def save_cookies(driver: WebDriver, filepath: Path) -> None:
    """
    Save browser cookies to file

    Args:
        driver: Selenium WebDriver instance
        filepath: Path to save cookies
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    try:
        cookies = driver.get_cookies()
        with open(filepath, 'wb') as f:
            pickle.dump(cookies, f)
        logger.info(f"Saved {len(cookies)} cookies to {filepath}")
    except Exception as e:
        logger.error(f"Error saving cookies: {e}")


def load_cookies(driver: WebDriver, filepath: Path) -> bool:
    """
    Load browser cookies from file

    Args:
        driver: Selenium WebDriver instance
        filepath: Path to cookie file

    Returns:
        True if cookies loaded successfully, False otherwise
    """
    if not filepath.exists():
        logger.warning(f"Cookie file not found: {filepath}")
        return False

    try:
        with open(filepath, 'rb') as f:
            cookies = pickle.load(f)

        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Error adding cookie {cookie.get('name')}: {e}")

        logger.info(f"Loaded {len(cookies)} cookies from {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return False


def save_screenshot(driver: WebDriver, filepath: Path, prefix: str = "screenshot") -> None:
    """
    Save a screenshot of the current page

    Args:
        driver: Selenium WebDriver instance
        filepath: Directory to save screenshot
        prefix: Filename prefix
    """
    filepath.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = filepath / f"{prefix}_{timestamp}.png"

    try:
        driver.save_screenshot(str(screenshot_path))
        logger.info(f"Screenshot saved to {screenshot_path}")
    except Exception as e:
        logger.error(f"Error saving screenshot: {e}")


def save_page_source(driver: WebDriver, filepath: Path, prefix: str = "page_source") -> None:
    """
    Save the page HTML source

    Args:
        driver: Selenium WebDriver instance
        filepath: Directory to save HTML
        prefix: Filename prefix
    """
    filepath.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    html_path = filepath / f"{prefix}_{timestamp}.html"

    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info(f"Page source saved to {html_path}")
    except Exception as e:
        logger.error(f"Error saving page source: {e}")


def check_for_captcha(driver: WebDriver) -> bool:
    """
    Check if a CAPTCHA is present on the page

    Args:
        driver: Selenium WebDriver instance

    Returns:
        True if CAPTCHA detected, False otherwise
    """
    captcha_indicators = [
        "g-recaptcha",
        "h-captcha",
        "px-captcha",
        "captcha-container",
        "challenge-container",
        "cf-challenge",
        "perimeterx"
    ]

    page_source = driver.page_source.lower()

    for indicator in captcha_indicators:
        if indicator in page_source:
            logger.warning(f"CAPTCHA detected: {indicator}")
            return True

    # Check for common CAPTCHA iframes
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            if "recaptcha" in src or "hcaptcha" in src or "perimeterx" in src:
                logger.warning(f"CAPTCHA iframe detected: {src}")
                return True
    except Exception as e:
        logger.debug(f"Error checking for CAPTCHA iframes: {e}")

    return False


def check_for_block(driver: WebDriver) -> bool:
    """
    Check if the page indicates blocking (403, access denied, etc.)

    Args:
        driver: Selenium WebDriver instance

    Returns:
        True if blocked, False otherwise
    """
    block_indicators = [
        "403 forbidden",
        "access denied",
        "you have been blocked",
        "your access has been blocked",
        "unusual traffic",
        "automated requests",
        "bot detected",
        "captcha required",
        "please verify you are a human",
        "enable javascript and cookies"
    ]

    page_text = driver.page_source.lower()

    for indicator in block_indicators:
        if indicator in page_text:
            logger.error(f"Block detected: {indicator}")
            return True

    # Check page title
    try:
        title = driver.title.lower()
        if any(ind in title for ind in ["403", "denied", "blocked", "error"]):
            logger.error(f"Block detected in title: {title}")
            return True
    except Exception:
        pass

    return False


def wait_for_page_load(driver: WebDriver, timeout: int = 30) -> bool:
    """
    Wait for page to fully load

    Args:
        driver: Selenium WebDriver instance
        timeout: Timeout in seconds

    Returns:
        True if page loaded, False if timeout
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logger.debug("Page loaded successfully")
        return True
    except TimeoutException:
        logger.warning("Page load timeout")
        return False


def parse_price(price_text: str) -> Optional[float]:
    """
    Parse price text to extract numeric value

    Args:
        price_text: Price string (e.g., "$1,500", "From $2000")

    Returns:
        Numeric price value or None
    """
    if not price_text:
        return None

    # Remove common text patterns
    price_text = price_text.lower()
    price_text = price_text.replace("starting at", "").replace("from", "").replace("starting price", "")

    # Extract numbers
    import re
    numbers = re.findall(r'\d+[,\d]*\.?\d*', price_text)

    if numbers:
        # Take the first number found
        number_str = numbers[0].replace(',', '')
        try:
            return float(number_str)
        except ValueError:
            return None

    return None
