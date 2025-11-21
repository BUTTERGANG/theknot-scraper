"""
Configuration settings for TheKnot scraper
"""
import os
from pathlib import Path
from typing import Optional, Tuple
from pydantic import BaseModel, Field

class ScraperConfig(BaseModel):
    """Configuration for the scraper"""

    # Browser settings
    headless: bool = Field(default=False, description="Run browser in headless mode (not recommended for anti-detection)")
    window_size: Tuple[int, int] = Field(default=(1920, 1080), description="Browser window size")

    # Timing settings (in seconds)
    min_delay: float = Field(default=2.0, description="Minimum delay between actions")
    max_delay: float = Field(default=5.0, description="Maximum delay between actions")
    page_load_timeout: int = Field(default=30, description="Page load timeout")
    scroll_pause: float = Field(default=0.5, description="Pause between scroll actions")

    # Human behavior simulation
    enable_mouse_movement: bool = Field(default=True, description="Simulate mouse movements")
    enable_random_scrolling: bool = Field(default=True, description="Random scrolling behavior")
    typing_delay_range: Tuple[float, float] = Field(default=(0.1, 0.3), description="Delay range for typing")

    # Retry settings
    max_retries: int = Field(default=3, description="Maximum number of retries for failed requests")
    retry_delay: int = Field(default=5, description="Delay between retries")

    # Proxy settings (optional)
    proxy: Optional[str] = Field(default=None, description="Proxy URL (e.g., 'http://user:pass@host:port')")
    proxy_type: str = Field(default="http", description="Proxy type: http, socks4, socks5")

    # CAPTCHA settings
    captcha_wait_time: int = Field(default=60, description="Time to wait for manual CAPTCHA solving")
    auto_solve_captcha: bool = Field(default=False, description="Attempt to solve CAPTCHAs automatically")
    captcha_service_key: Optional[str] = Field(default=None, description="API key for CAPTCHA solving service")

    # Output settings
    output_dir: Path = Field(default=Path("./output"), description="Directory for output files")
    save_screenshots: bool = Field(default=True, description="Save screenshots on errors")
    save_html: bool = Field(default=False, description="Save page HTML for debugging")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[Path] = Field(default=Path("./logs/scraper.log"), description="Log file path")

    # Session management
    save_cookies: bool = Field(default=True, description="Save cookies between sessions")
    cookie_file: Path = Field(default=Path("./cookies/theknot_cookies.pkl"), description="Cookie file path")

    # User agent rotation
    rotate_user_agent: bool = Field(default=False, description="Rotate user agent (not recommended - breaks fingerprint)")
    custom_user_agent: Optional[str] = Field(default=None, description="Custom user agent string")

    class Config:
        env_prefix = "THEKNOT_"
        env_file = ".env"
        env_file_encoding = "utf-8"


# Default configuration instance
DEFAULT_CONFIG = ScraperConfig()


# Browser arguments for stealth
CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-gpu",
    "--disable-notifications",
    "--disable-popup-blocking",
    "--start-maximized",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
]


# Chrome preferences to avoid detection
CHROME_PREFS = {
    "profile.default_content_setting_values.notifications": 2,
    "profile.managed_default_content_settings.images": 1,
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False,
    "profile.default_content_settings.popups": 0,
    "download.prompt_for_download": False,
    "download.default_directory": "/tmp",
    "safebrowsing.enabled": True,
}


# Realistic browser headers (will be set by browser, but can be validated)
BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


# TheKnot specific selectors (CSS)
SELECTORS = {
    "vendor_name": [
        "h1.ods-c-text-hero-v1",
        "[class*='text-hero--mp-']",
        ".vendor-name-container--mp-4b058 h1",
        "[class*='vendor-name-container'] h1",
        "h1.vendor-name",
        "h1[data-testid='vendor-name']",
    ],
    "starting_price": [
        "[data-testid='meta-price-range']",
        "[class*='price--mp-']",
        ".price--mp-28150",
        "[data-testid='starting-price']",
        ".starting-price",
    ],
    "packages_section": [
        "[class*='pricesAndPackages--mp-']",
        ".pricesAndPackages--mp-f70fc",
        "[data-testid='packages-section']",
        ".packages-container",
        "#packages",
    ],
    "package_item": [
        "[class*='package-wrapper--mp-']",
        ".package-wrapper--mp-655e4",
        "[class*='package-container--mp-']",
        ".package-container--mp-143a9",
        ".package-card",
        "[data-testid='package']",
    ],
    "package_name": [
        "[class*='package-name--mp-']",
        ".package-name--mp-902d9",
        "[class*='package-heading--mp-']",
        ".package-heading--mp-3fb73",
        ".package-name",
        "[data-testid='package-name']",
    ],
    "package_price": [
        "[class*='package-price--mp-']",
        ".package-price--mp-646e1",
        ".package-price",
        "[data-testid='package-price']",
    ],
    "package_description": [
        ".package-description",
        ".package-details",
        "[data-testid='package-description']",
        ".package-features",
    ],
    # Marketplace/Search Results page selectors
    "search_result_cards": [
        "[class*='vendor-card']",
        "[class*='VendorCard']",
        "[data-testid='vendor-card']",
        "[class*='search-result']",
        ".vendor-card",
        "article[class*='vendor']",
        "div[class*='storefrontCard']",
        "[data-component='StorefrontCard']",
    ],
    "vendor_card_link": [
        "a[href*='/marketplace/'][href*='--']",  # Links to individual vendors have -- in URL
        "[class*='vendor-card'] a[href*='/marketplace/']",
        "[class*='VendorCard'] a[href*='/marketplace/']",
        "a[data-testid='vendor-link']",
        ".vendor-card-link",
    ],
    "vendor_card_name": [
        "[class*='vendor-card'] h2",
        "[class*='vendor-card'] h3",
        "[class*='VendorCard'] h2",
        "[class*='VendorCard'] h3",
        ".vendor-card-title",
        "[data-testid='vendor-name']",
    ],
}


# XPath alternatives for selectors
XPATH_SELECTORS = {
    "vendor_name": [
        "//h1[contains(@class, 'text-hero')]",
        "//h1[contains(@class, 'ods-c-text-hero')]",
        "//*[contains(@class, 'vendor-name-container')]//h1",
        "//h1[contains(@class, 'vendor-name')]",
    ],
    "starting_price": [
        "//*[@data-testid='meta-price-range']",
        "//*[contains(@class, 'price--mp-')]",
        "//*[contains(@class, 'starting-price')]",
    ]
}
