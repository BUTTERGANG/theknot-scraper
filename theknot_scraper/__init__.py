"""
TheKnot.com Web Scraper with Advanced Anti-Detection

A sophisticated web scraping solution designed to extract vendor information
from TheKnot.com while bypassing multi-layered bot detection mechanisms.
"""

__version__ = "1.0.0"
__author__ = "Security Research Team"

from .scraper import TheKnotScraper, VendorData
from .config import ScraperConfig

__all__ = ["TheKnotScraper", "VendorData", "ScraperConfig"]
