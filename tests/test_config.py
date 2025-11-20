"""
Tests for configuration module
"""
import pytest
from pathlib import Path
from theknot_scraper.config import ScraperConfig, SELECTORS, CHROME_ARGS


class TestScraperConfig:
    """Test ScraperConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ScraperConfig()

        assert config.headless is False
        assert config.window_size == (1920, 1080)
        assert config.min_delay == 2.0
        assert config.max_delay == 5.0
        assert config.enable_mouse_movement is True
        assert config.enable_random_scrolling is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = ScraperConfig(
            headless=True,
            min_delay=1.0,
            max_delay=3.0,
            log_level="DEBUG"
        )

        assert config.headless is True
        assert config.min_delay == 1.0
        assert config.max_delay == 3.0
        assert config.log_level == "DEBUG"

    def test_typing_delay_range(self):
        """Test typing delay range configuration"""
        config = ScraperConfig()
        assert isinstance(config.typing_delay_range, tuple)
        assert len(config.typing_delay_range) == 2
        assert config.typing_delay_range[0] < config.typing_delay_range[1]

    def test_retry_settings(self):
        """Test retry configuration"""
        config = ScraperConfig(max_retries=5, retry_delay=10)

        assert config.max_retries == 5
        assert config.retry_delay == 10

    def test_proxy_config(self):
        """Test proxy configuration"""
        config = ScraperConfig(
            proxy="http://user:pass@proxy.com:8080",
            proxy_type="http"
        )

        assert config.proxy == "http://user:pass@proxy.com:8080"
        assert config.proxy_type == "http"

    def test_path_configs(self):
        """Test path-based configurations"""
        config = ScraperConfig()

        assert isinstance(config.output_dir, Path)
        assert isinstance(config.log_file, Path)
        assert isinstance(config.cookie_file, Path)


class TestSelectors:
    """Test selector definitions"""

    def test_selectors_structure(self):
        """Test that SELECTORS dict has expected structure"""
        assert isinstance(SELECTORS, dict)

        # Check required keys
        required_keys = [
            "vendor_name",
            "starting_price",
            "packages_section",
            "package_item",
        ]

        for key in required_keys:
            assert key in SELECTORS
            assert isinstance(SELECTORS[key], list)
            assert len(SELECTORS[key]) > 0

    def test_selectors_are_strings(self):
        """Test that all selectors are strings"""
        for element_type, selectors in SELECTORS.items():
            for selector in selectors:
                assert isinstance(selector, str)
                assert len(selector) > 0


class TestChromeArgs:
    """Test Chrome arguments"""

    def test_chrome_args_list(self):
        """Test that CHROME_ARGS is a list"""
        assert isinstance(CHROME_ARGS, list)
        assert len(CHROME_ARGS) > 0

    def test_chrome_args_contain_required(self):
        """Test that required arguments are present"""
        required_flags = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]

        for flag in required_flags:
            assert flag in CHROME_ARGS
