"""
Pytest configuration and fixtures
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "theknot_scraper"))

from theknot_scraper.config import ScraperConfig


@pytest.fixture
def test_config():
    """Provide a test configuration"""
    return ScraperConfig(
        headless=True,
        min_delay=0.1,  # Fast for testing
        max_delay=0.2,
        enable_mouse_movement=False,
        enable_random_scrolling=False,
        save_screenshots=False,
        save_html=False,
        log_level="ERROR",  # Reduce noise in tests
    )


@pytest.fixture
def mock_driver():
    """Provide a mocked Selenium WebDriver"""
    driver = MagicMock()
    driver.page_source = "<html><body>Test Page</body></html>"
    driver.title = "Test Page"
    driver.current_url = "https://test.com"
    return driver


@pytest.fixture
def sample_html():
    """Provide sample HTML for testing selectors"""
    return """
    <html>
        <head><title>Test Vendor Page</title></head>
        <body>
            <h1 class="vendor-name">Test Venue</h1>
            <div class="starting-price">From $2,500</div>
            <section class="packages">
                <div class="package-item">
                    <h3 class="package-name">Basic Package</h3>
                    <span class="package-price">$1,500</span>
                    <p class="package-description">Basic package description</p>
                </div>
                <div class="package-item">
                    <h3 class="package-name">Premium Package</h3>
                    <span class="package-price">$3,500</span>
                    <p class="package-description">Premium package description</p>
                </div>
            </section>
        </body>
    </html>
    """


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide a temporary output directory"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
