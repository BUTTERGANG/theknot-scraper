"""
TheKnot.com Web Scraper with Advanced Anti-Detection

This scraper is designed to bypass the multi-layered bot detection
mechanisms identified in the bot detection analysis.
"""
import time
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from loguru import logger

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import ScraperConfig, CHROME_ARGS, CHROME_PREFS, SELECTORS, XPATH_SELECTORS
from utils import (
    random_delay, simulate_human_behavior, safe_find_element, safe_find_elements,
    extract_text, save_cookies, load_cookies, save_screenshot, save_page_source,
    check_for_captcha, check_for_block, wait_for_page_load, parse_price
)


@dataclass
class VendorData:
    """Data structure for vendor information"""
    url: str
    business_name: str = ""
    starting_price: str = ""
    starting_price_numeric: Optional[float] = None
    packages: List[Dict[str, str]] = None
    raw_packages_html: str = ""
    scrape_timestamp: str = ""
    success: bool = False
    error_message: str = ""

    def __post_init__(self):
        if self.packages is None:
            self.packages = []

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


class TheKnotScraper:
    """
    Advanced web scraper for TheKnot.com with anti-detection measures
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize the scraper

        Args:
            config: ScraperConfig instance (uses default if None)
        """
        self.config = config or ScraperConfig()
        self.driver: Optional[uc.Chrome] = None
        self.setup_logging()

        logger.info("TheKnot Scraper initialized")
        logger.info(f"Headless mode: {self.config.headless}")
        logger.info(f"Human behavior simulation: {self.config.enable_mouse_movement and self.config.enable_random_scrolling}")

    def setup_logging(self) -> None:
        """Configure logging"""
        logger.remove()  # Remove default handler

        # Console logging
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=self.config.log_level,
            colorize=True
        )

        # File logging
        if self.config.log_file:
            self.config.log_file.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                self.config.log_file,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
                level=self.config.log_level,
                rotation="10 MB",
                retention="7 days"
            )

    def setup_driver(self) -> None:
        """
        Initialize undetected ChromeDriver with anti-detection options
        """
        logger.info("Setting up undetected ChromeDriver")

        try:
            options = uc.ChromeOptions()

            # Add stealth arguments
            for arg in CHROME_ARGS:
                if arg == "--start-maximized" and self.config.headless:
                    continue  # Skip in headless mode
                options.add_argument(arg)

            # Set window size
            options.add_argument(f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}")

            # Headless mode (not recommended for anti-detection)
            if self.config.headless:
                logger.warning("Headless mode enabled - detection risk is higher!")
                options.add_argument("--headless=new")

            # Set preferences
            options.add_experimental_option("prefs", CHROME_PREFS)

            # Exclude automation flags (handled by undetected-chromedriver internally)
            # Commenting out to fix compatibility issues with newer Chrome/Python versions
            # options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            # options.add_experimental_option("useAutomationExtension", False)

            # Custom user agent (optional)
            if self.config.custom_user_agent:
                options.add_argument(f"--user-agent={self.config.custom_user_agent}")

            # Proxy configuration
            if self.config.proxy:
                logger.info(f"Using proxy: {self.config.proxy}")
                options.add_argument(f"--proxy-server={self.config.proxy}")

            # Initialize undetected Chrome
            self.driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect Chrome version
                driver_executable_path=None,  # Auto-download if needed
            )

            # Set page load timeout
            self.driver.set_page_load_timeout(self.config.page_load_timeout)

            # Additional stealth measures
            self._apply_stealth_scripts()

            logger.info("ChromeDriver initialized successfully")

        except Exception as e:
            logger.error(f"Error setting up ChromeDriver: {e}")
            raise

    def _apply_stealth_scripts(self) -> None:
        """
        Apply JavaScript-based stealth measures to avoid detection
        """
        if not self.driver:
            return

        logger.debug("Applying stealth scripts")

        # Override navigator.webdriver
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })

        # Override Chrome detection
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                window.navigator.chrome = {
                    runtime: {},
                };
            """
        })

        # Override permissions API
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """
        })

        # Override plugins length
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """
        })

        # Override languages
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """
        })

        # Randomize canvas fingerprint slightly (but consistently within session)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                const getImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function() {
                    const imageData = getImageData.apply(this, arguments);
                    // Add minimal noise to avoid perfect fingerprint matching
                    // but keep it consistent for this session
                    return imageData;
                };
            """
        })

        # Override automation detection flags
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                delete navigator.__proto__.webdriver;

                // Override Selenium/Puppeteer detection
                if (window.document) {
                    const originalGetter = Object.getOwnPropertyDescriptor(
                        window.Document.prototype,
                        'documentElement'
                    ).get;

                    Object.defineProperty(window.Document.prototype, 'documentElement', {
                        get: function() {
                            const element = originalGetter.call(this);
                            if (element && element.hasAttribute('webdriver')) {
                                element.removeAttribute('webdriver');
                            }
                            return element;
                        }
                    });
                }
            """
        })

        # Add realistic touch support
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'maxTouchPoints', {
                    get: () => 1
                });
            """
        })

    def navigate_to_page(self, url: str, wait_time: int = 3, retry: int = 0) -> bool:
        """
        Navigate to a URL with human-like behavior and retry logic

        Args:
            url: URL to navigate to
            wait_time: Time to wait after navigation
            retry: Current retry attempt number

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.setup_driver()

        max_retries = self.config.max_retries

        try:
            logger.info(f"Navigating to: {url}" + (f" (attempt {retry + 1}/{max_retries + 1})" if retry > 0 else ""))

            # Load cookies before navigation if available
            if self.config.save_cookies and self.config.cookie_file.exists():
                # Navigate to domain first to set cookies
                domain = url.split('/')[2]
                try:
                    self.driver.get(f"https://{domain}")
                    load_cookies(self.driver, self.config.cookie_file)
                    logger.debug("Loaded existing cookies")
                except Exception as e:
                    logger.debug(f"Could not load cookies: {e}")

            # Navigate to page
            self.driver.get(url)

            # Wait for page load
            wait_for_page_load(self.driver, self.config.page_load_timeout)

            # Random delay
            random_delay(wait_time, wait_time + 2)

            # Check for blocks or CAPTCHAs
            if check_for_block(self.driver):
                logger.error("Page indicates we are blocked")
                if self.config.save_screenshots:
                    save_screenshot(self.driver, self.config.output_dir, "blocked")

                # Retry with longer delay
                if retry < max_retries:
                    logger.info(f"Retrying after {self.config.retry_delay} seconds...")
                    time.sleep(self.config.retry_delay)
                    return self.navigate_to_page(url, wait_time, retry + 1)

                return False

            if check_for_captcha(self.driver):
                logger.warning("CAPTCHA detected on page")
                if self.config.auto_solve_captcha:
                    logger.info("Attempting to solve CAPTCHA...")
                    # TODO: Implement CAPTCHA solving
                    pass
                else:
                    logger.warning(f"Waiting {self.config.captcha_wait_time} seconds for manual CAPTCHA solving...")
                    time.sleep(self.config.captcha_wait_time)

            # Simulate human behavior
            simulate_human_behavior(self.driver, self.config)

            # Save cookies if enabled
            if self.config.save_cookies:
                save_cookies(self.driver, self.config.cookie_file)

            logger.info("Navigation successful")
            return True

        except TimeoutException:
            logger.error(f"Timeout loading page: {url}")
            if retry < max_retries:
                logger.info(f"Retrying after {self.config.retry_delay} seconds...")
                time.sleep(self.config.retry_delay)
                return self.navigate_to_page(url, wait_time, retry + 1)
            return False
        except Exception as e:
            logger.error(f"Error navigating to page: {e}")
            if retry < max_retries:
                logger.info(f"Retrying after {self.config.retry_delay} seconds...")
                time.sleep(self.config.retry_delay)
                return self.navigate_to_page(url, wait_time, retry + 1)
            return False

    def detect_page_type(self) -> str:
        """
        Detect if current page is a marketplace listing or individual vendor page

        Returns:
            "marketplace" for search/listing pages
            "vendor" for individual vendor pages
            "unknown" if unable to determine
        """
        if not self.driver:
            return "unknown"

        try:
            url = self.driver.current_url
            logger.debug(f"Detecting page type for: {url}")

            # Check URL pattern
            if '/marketplace/' in url:
                # Extract the part after /marketplace/
                path_parts = url.split('/marketplace/')[-1].split('?')[0].split('/')

                # Marketplace listing: /marketplace/category-location
                # Vendor page: /marketplace/vendor-name-location--vendor-id
                # Vendor pages typically have "--" followed by an ID
                if '--' in path_parts[0]:
                    logger.info("Detected vendor page (URL contains --)")
                    return "vendor"
                elif len(path_parts) == 1:
                    logger.info("Detected marketplace listing page")
                    return "marketplace"

            # Fallback: Try to detect by page content
            # Marketplace pages have multiple vendor cards
            vendor_cards = safe_find_elements(self.driver, SELECTORS["search_result_cards"])
            if vendor_cards and len(vendor_cards) > 1:
                logger.info(f"Detected marketplace page ({len(vendor_cards)} vendor cards found)")
                return "marketplace"

            # Vendor pages have a single business name h1
            vendor_name = safe_find_element(self.driver, SELECTORS["vendor_name"])
            if vendor_name:
                logger.info("Detected vendor page (has vendor name h1)")
                return "vendor"

            logger.warning("Unable to determine page type")
            return "unknown"

        except Exception as e:
            logger.error(f"Error detecting page type: {e}")
            return "unknown"

    def scrape_marketplace_page(self, url: str, max_vendors: Optional[int] = None) -> List[str]:
        """
        Scrape marketplace/search page to extract vendor URLs

        Args:
            url: Marketplace listing URL
            max_vendors: Maximum number of vendor URLs to extract (None = all)

        Returns:
            List of vendor page URLs
        """
        logger.info(f"Scraping marketplace page: {url}")

        vendor_urls = []

        # Navigate to page
        if not self.navigate_to_page(url):
            logger.error("Failed to navigate to marketplace page")
            return vendor_urls

        # Verify it's a marketplace page
        page_type = self.detect_page_type()
        if page_type != "marketplace":
            logger.warning(f"Page type detected as '{page_type}', not 'marketplace'")
            if page_type == "vendor":
                logger.info("This appears to be a vendor page. Returning this URL.")
                return [url]

        try:
            # Find all vendor cards
            vendor_cards = safe_find_elements(self.driver, SELECTORS["search_result_cards"])

            if not vendor_cards:
                logger.warning("No vendor cards found on marketplace page")
                if self.config.save_screenshots:
                    save_screenshot(self.driver, self.config.output_dir, "marketplace_no_results")
                if self.config.save_html:
                    save_page_source(self.driver, self.config.output_dir, "marketplace_no_results")
                return vendor_urls

            logger.info(f"Found {len(vendor_cards)} vendor cards")

            # Extract vendor URLs
            for idx, card in enumerate(vendor_cards, 1):
                if max_vendors and len(vendor_urls) >= max_vendors:
                    break

                try:
                    # Try to find link within this card
                    link_element = None

                    # Try each selector
                    for selector in SELECTORS["vendor_card_link"]:
                        try:
                            link_element = card.find_element(By.CSS_SELECTOR, selector)
                            if link_element:
                                break
                        except Exception:
                            continue

                    if not link_element:
                        # Try finding any link with /marketplace/ in href
                        try:
                            links = card.find_elements(By.CSS_SELECTOR, "a[href*='/marketplace/']")
                            for link in links:
                                href = link.get_attribute("href")
                                if href and '--' in href:  # Vendor URLs have -- in them
                                    link_element = link
                                    break
                        except Exception:
                            pass

                    if link_element:
                        vendor_url = link_element.get_attribute("href")
                        if vendor_url and vendor_url not in vendor_urls:
                            # Validate it's a vendor URL
                            if '/marketplace/' in vendor_url and '--' in vendor_url:
                                vendor_urls.append(vendor_url)
                                logger.debug(f"Found vendor URL {len(vendor_urls)}: {vendor_url}")
                            else:
                                logger.debug(f"Skipping non-vendor URL: {vendor_url}")
                    else:
                        logger.debug(f"No link found in vendor card {idx}")

                except Exception as e:
                    logger.debug(f"Error extracting URL from vendor card {idx}: {e}")

            logger.info(f"Extracted {len(vendor_urls)} vendor URLs from marketplace page")

            if not vendor_urls:
                logger.warning("No vendor URLs extracted. Saving debug info...")
                if self.config.save_screenshots:
                    save_screenshot(self.driver, self.config.output_dir, "marketplace_no_urls")
                if self.config.save_html:
                    save_page_source(self.driver, self.config.output_dir, "marketplace_no_urls")

            return vendor_urls

        except Exception as e:
            logger.error(f"Error scraping marketplace page: {e}")
            if self.config.save_screenshots:
                save_screenshot(self.driver, self.config.output_dir, "marketplace_error")
            return vendor_urls

    def get_page_html(self, url: str) -> Tuple[bool, str, str]:
        """
        Simply fetch a page and return its HTML

        Args:
            url: URL to fetch

        Returns:
            Tuple of (success, html, error_message)
        """
        logger.info(f"Fetching HTML from: {url}")

        if not self.navigate_to_page(url):
            return False, "", "Failed to navigate to page"

        try:
            html = self.driver.page_source

            # Log page info
            title = self.driver.title
            logger.info(f"Page title: {title}")
            logger.info(f"HTML length: {len(html)} characters")

            # Save HTML if configured
            if self.config.save_html:
                save_page_source(self.driver, self.config.output_dir, "fetched_page")

            # Save screenshot
            if self.config.save_screenshots:
                save_screenshot(self.driver, self.config.output_dir, "fetched_page")

            return True, html, ""

        except Exception as e:
            error_msg = f"Error getting page HTML: {e}"
            logger.error(error_msg)
            return False, "", error_msg

    def scrape_vendor_page(self, url: str) -> VendorData:
        """
        Scrape vendor information from a vendor page

        Args:
            url: Vendor page URL

        Returns:
            VendorData object with scraped information
        """
        logger.info(f"Scraping vendor page: {url}")

        vendor_data = VendorData(url=url)
        vendor_data.scrape_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Navigate to page
        if not self.navigate_to_page(url):
            vendor_data.error_message = "Failed to navigate to page"
            return vendor_data

        try:
            # Extract business name
            vendor_data.business_name = self._extract_business_name()

            # Extract starting price
            price_text = self._extract_starting_price()
            vendor_data.starting_price = price_text
            vendor_data.starting_price_numeric = parse_price(price_text)

            # Extract packages
            vendor_data.packages = self._extract_packages()

            # Get raw packages HTML
            vendor_data.raw_packages_html = self._extract_packages_html()

            # Mark as successful if we got at least the business name
            if vendor_data.business_name:
                vendor_data.success = True
                logger.info(f"Successfully scraped: {vendor_data.business_name}")
            else:
                vendor_data.error_message = "Could not extract business name"
                logger.warning("Scraping incomplete - no business name found")

            # Save debugging info if enabled
            if self.config.save_screenshots:
                save_screenshot(self.driver, self.config.output_dir, "vendor_page")

            if self.config.save_html:
                save_page_source(self.driver, self.config.output_dir, "vendor_page")

        except Exception as e:
            logger.error(f"Error scraping vendor page: {e}")
            vendor_data.error_message = str(e)

            if self.config.save_screenshots:
                save_screenshot(self.driver, self.config.output_dir, "error")

        return vendor_data

    def _extract_business_name(self) -> str:
        """Extract business name from vendor page"""
        logger.debug("Extracting business name")

        element = safe_find_element(self.driver, SELECTORS["vendor_name"])
        if element:
            name = extract_text(element)
            logger.info(f"Found business name: {name}")
            return name

        # Try XPath as fallback
        element = safe_find_element(self.driver, XPATH_SELECTORS["vendor_name"], By.XPATH)
        if element:
            name = extract_text(element)
            logger.info(f"Found business name (XPath): {name}")
            return name

        logger.warning("Could not find business name")
        return ""

    def _extract_starting_price(self) -> str:
        """Extract starting price from vendor page"""
        logger.debug("Extracting starting price")

        element = safe_find_element(self.driver, SELECTORS["starting_price"])
        if element:
            price = extract_text(element)
            logger.info(f"Found starting price: {price}")
            return price

        # Try XPath as fallback
        element = safe_find_element(self.driver, XPATH_SELECTORS["starting_price"], By.XPATH)
        if element:
            price = extract_text(element)
            logger.info(f"Found starting price (XPath): {price}")
            return price

        logger.warning("Could not find starting price")
        return ""

    def _extract_packages(self) -> List[Dict[str, str]]:
        """Extract package information from vendor page"""
        logger.debug("Extracting packages")

        packages = []

        # Find packages container
        container = safe_find_element(self.driver, SELECTORS["packages_section"])

        if not container:
            logger.warning("Could not find packages section")
            return packages

        # Find individual package items
        package_elements = safe_find_elements(self.driver, SELECTORS["package_item"])

        if not package_elements:
            logger.warning("Could not find package items")
            return packages

        logger.info(f"Found {len(package_elements)} packages")

        for idx, package_elem in enumerate(package_elements, 1):
            try:
                package_data = {
                    "package_number": idx,
                    "name": "",
                    "price": "",
                    "description": ""
                }

                # Extract package name
                try:
                    name_elem = package_elem.find_element(By.CSS_SELECTOR, ", ".join(SELECTORS["package_name"]))
                    package_data["name"] = extract_text(name_elem)
                except Exception:
                    logger.debug(f"Could not find name for package {idx}")

                # Extract package price
                try:
                    price_elem = package_elem.find_element(By.CSS_SELECTOR, ", ".join(SELECTORS["package_price"]))
                    package_data["price"] = extract_text(price_elem)
                except Exception:
                    logger.debug(f"Could not find price for package {idx}")

                # Extract package description
                try:
                    desc_elem = package_elem.find_element(By.CSS_SELECTOR, ", ".join(SELECTORS["package_description"]))
                    package_data["description"] = extract_text(desc_elem)
                except Exception:
                    logger.debug(f"Could not find description for package {idx}")

                packages.append(package_data)
                logger.debug(f"Package {idx}: {package_data['name']} - {package_data['price']}")

            except Exception as e:
                logger.warning(f"Error extracting package {idx}: {e}")

        return packages

    def _extract_packages_html(self) -> str:
        """Extract raw HTML of packages section"""
        logger.debug("Extracting packages HTML")

        element = safe_find_element(self.driver, SELECTORS["packages_section"])
        if element:
            try:
                html = element.get_attribute("outerHTML")
                return html
            except Exception as e:
                logger.warning(f"Error getting packages HTML: {e}")

        return ""

    def scrape_multiple_vendors(self, urls: List[str]) -> List[VendorData]:
        """
        Scrape multiple vendor pages

        Args:
            urls: List of vendor page URLs

        Returns:
            List of VendorData objects
        """
        logger.info(f"Scraping {len(urls)} vendor pages")

        results = []

        for idx, url in enumerate(urls, 1):
            logger.info(f"Processing vendor {idx}/{len(urls)}")

            # Scrape vendor
            vendor_data = self.scrape_vendor_page(url)
            results.append(vendor_data)

            # Random delay between requests
            if idx < len(urls):
                delay = random_delay(self.config.min_delay, self.config.max_delay)
                logger.info(f"Waiting before next vendor...")

        logger.info(f"Completed scraping {len(results)} vendors")
        successful = sum(1 for v in results if v.success)
        logger.info(f"Successful: {successful}/{len(results)}")

        return results

    def close(self) -> None:
        """Close the browser and cleanup"""
        if self.driver:
            logger.info("Closing browser")
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            self.driver = None

    def __enter__(self):
        """Context manager entry"""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
