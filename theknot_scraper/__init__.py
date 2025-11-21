"""
TheKnot.com Web Scraper with Advanced Anti-Detection

A sophisticated web scraping solution designed to extract vendor information
from TheKnot.com while bypassing multi-layered bot detection mechanisms.
"""

__version__ = "1.0.0"
__author__ = "Security Research Team"

from .config import ScraperConfig

__all__ = ["TheKnotScraper", "VendorData", "ScraperConfig"]


def __getattr__(name):
    """Lazy import for scraper module to avoid import errors when dependencies are missing."""
    if name in ("TheKnotScraper", "VendorData"):
        from .scraper import TheKnotScraper, VendorData
        return TheKnotScraper if name == "TheKnotScraper" else VendorData
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
