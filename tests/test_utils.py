"""
Tests for utility functions
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from theknot_scraper.utils import (
    random_delay,
    parse_price,
    extract_text,
    check_for_captcha,
    check_for_block,
)


class TestRandomDelay:
    """Test random_delay function"""

    def test_delay_within_range(self):
        """Test that delay is within specified range"""
        start = time.time()
        random_delay(0.1, 0.2)
        elapsed = time.time() - start

        assert 0.09 <= elapsed <= 0.25  # Allow small variance

    def test_delay_accepts_same_min_max(self):
        """Test that same min and max works"""
        start = time.time()
        random_delay(0.1, 0.1)
        elapsed = time.time() - start

        assert 0.09 <= elapsed <= 0.15


class TestParsePrice:
    """Test parse_price function"""

    def test_parse_simple_price(self):
        """Test parsing simple price"""
        assert parse_price("$1500") == 1500.0
        assert parse_price("$2000") == 2000.0

    def test_parse_price_with_comma(self):
        """Test parsing price with comma"""
        assert parse_price("$1,500") == 1500.0
        assert parse_price("$10,000") == 10000.0
        assert parse_price("$100,000") == 100000.0

    def test_parse_price_with_decimal(self):
        """Test parsing price with decimal"""
        assert parse_price("$1,500.50") == 1500.5
        assert parse_price("$2000.99") == 2000.99

    def test_parse_price_with_text(self):
        """Test parsing price with surrounding text"""
        assert parse_price("Starting at $1,500") == 1500.0
        assert parse_price("From $2,000") == 2000.0
        assert parse_price("Starting price $3000") == 3000.0

    def test_parse_price_invalid(self):
        """Test parsing invalid price strings"""
        assert parse_price("") is None
        assert parse_price("TBD") is None
        assert parse_price("Contact for pricing") is None
        assert parse_price("Price upon request") is None

    def test_parse_price_no_numbers(self):
        """Test parsing text with no numbers"""
        assert parse_price("No pricing available") is None


class TestExtractText:
    """Test extract_text function"""

    def test_extract_from_element_text(self):
        """Test extracting from element.text"""
        element = Mock()
        element.text = "  Test Text  "

        result = extract_text(element)
        assert result == "Test Text"

    def test_extract_from_text_content(self):
        """Test fallback to textContent"""
        element = Mock()
        element.text = ""
        element.get_attribute.side_effect = lambda attr: (
            "  Content Text  " if attr == "textContent" else ""
        )

        result = extract_text(element)
        assert result == "Content Text"

    def test_extract_from_inner_text(self):
        """Test fallback to innerText"""
        element = Mock()
        element.text = ""
        element.get_attribute.side_effect = lambda attr: (
            "  Inner Text  " if attr == "innerText" else ""
        )

        result = extract_text(element)
        assert result == "Inner Text"

    def test_extract_from_none(self):
        """Test extracting from None element"""
        result = extract_text(None)
        assert result == ""

    def test_extract_handles_exception(self):
        """Test that exceptions are handled gracefully"""
        element = Mock()
        element.text = Mock(side_effect=Exception("Test error"))

        result = extract_text(element)
        assert result == ""


class TestCheckForCaptcha:
    """Test check_for_captcha function"""

    def test_detects_recaptcha(self):
        """Test detection of reCAPTCHA"""
        driver = Mock()
        driver.page_source = "<html><div class='g-recaptcha'></div></html>"
        driver.find_elements.return_value = []

        assert check_for_captcha(driver) is True

    def test_detects_hcaptcha(self):
        """Test detection of hCaptcha"""
        driver = Mock()
        driver.page_source = "<html><div class='h-captcha'></div></html>"
        driver.find_elements.return_value = []

        assert check_for_captcha(driver) is True

    def test_detects_perimeterx_captcha(self):
        """Test detection of PerimeterX CAPTCHA"""
        driver = Mock()
        driver.page_source = "<html><div id='px-captcha'></div></html>"
        driver.find_elements.return_value = []

        assert check_for_captcha(driver) is True

    def test_no_captcha(self):
        """Test when no CAPTCHA is present"""
        driver = Mock()
        driver.page_source = "<html><body>Normal page</body></html>"
        driver.find_elements.return_value = []

        assert check_for_captcha(driver) is False


class TestCheckForBlock:
    """Test check_for_block function"""

    def test_detects_403_forbidden(self):
        """Test detection of 403 Forbidden"""
        driver = Mock()
        driver.page_source = "<html><body>403 Forbidden</body></html>"
        driver.title = "403 Forbidden"

        assert check_for_block(driver) is True

    def test_detects_access_denied(self):
        """Test detection of Access Denied"""
        driver = Mock()
        driver.page_source = "<html><body>Access Denied</body></html>"
        driver.title = "Page"

        assert check_for_block(driver) is True

    def test_detects_blocked_text(self):
        """Test detection of blocked text"""
        driver = Mock()
        driver.page_source = "<html><body>You have been blocked</body></html>"
        driver.title = "Page"

        assert check_for_block(driver) is True

    def test_no_block(self):
        """Test when page is not blocked"""
        driver = Mock()
        driver.page_source = "<html><body>Welcome to our site</body></html>"
        driver.title = "Home Page"

        assert check_for_block(driver) is False

    def test_title_check(self):
        """Test blocking detection via title"""
        driver = Mock()
        driver.page_source = "<html><body>Page content</body></html>"
        driver.title = "403 - Access Denied"

        assert check_for_block(driver) is True
