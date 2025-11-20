#!/usr/bin/env python3
"""
Validation script to check if all dependencies are installed correctly
and the scraper can be imported without errors.
"""
import sys
from pathlib import Path

def print_status(check_name, success, message=""):
    """Print check status"""
    status = "✅" if success else "❌"
    print(f"{status} {check_name}", end="")
    if message:
        print(f": {message}")
    else:
        print()


def validate_python_version():
    """Check Python version"""
    version = sys.version_info
    success = version.major == 3 and version.minor >= 8
    print_status(
        "Python version",
        success,
        f"{version.major}.{version.minor}.{version.micro}" +
        (" (OK)" if success else " (Need 3.8+)")
    )
    return success


def validate_imports():
    """Check if all required packages can be imported"""
    packages = {
        "undetected_chromedriver": "undetected-chromedriver",
        "selenium": "selenium",
        "loguru": "loguru",
        "pydantic": "pydantic",
    }

    all_success = True

    for module, package in packages.items():
        try:
            __import__(module)
            print_status(f"Package: {package}", True)
        except ImportError as e:
            print_status(f"Package: {package}", False, str(e))
            all_success = False

    return all_success


def validate_scraper_imports():
    """Check if scraper modules can be imported"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))

        from config import ScraperConfig, SELECTORS
        print_status("Import config.py", True)

        from utils import random_delay, simulate_human_behavior
        print_status("Import utils.py", True)

        from scraper import TheKnotScraper, VendorData
        print_status("Import scraper.py", True)

        # Try to instantiate config
        config = ScraperConfig()
        print_status("Instantiate ScraperConfig", True)

        return True

    except Exception as e:
        print_status("Import scraper modules", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def check_directories():
    """Check if required directories exist"""
    base_dir = Path(__file__).parent
    dirs = ["output", "logs", "cookies"]

    for dir_name in dirs:
        dir_path = base_dir / dir_name
        exists = dir_path.exists()
        if not exists:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print_status(f"Directory: {dir_name}/", True, "created")
            except Exception as e:
                print_status(f"Directory: {dir_name}/", False, str(e))
                return False
        else:
            print_status(f"Directory: {dir_name}/", True, "exists")

    return True


def check_chrome():
    """Check if Chrome/Chromium is installed"""
    import subprocess

    browsers = [
        ("google-chrome", "Google Chrome"),
        ("chromium", "Chromium"),
        ("chromium-browser", "Chromium Browser"),
    ]

    for cmd, name in browsers:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print_status(f"Browser: {name}", True, version)
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    print_status("Browser: Chrome/Chromium", False, "Not found - please install Chrome")
    return False


def main():
    """Run all validation checks"""
    print("=" * 70)
    print("TheKnot Scraper - Setup Validation")
    print("=" * 70)
    print()

    checks = [
        ("Python Version", validate_python_version),
        ("Required Packages", validate_imports),
        ("Scraper Modules", validate_scraper_imports),
        ("Directories", check_directories),
        ("Chrome Browser", check_chrome),
    ]

    results = []

    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * 70)
        try:
            success = check_func()
            results.append((check_name, success))
        except Exception as e:
            print_status(check_name, False, f"Exception: {e}")
            results.append((check_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print()

    all_passed = all(success for _, success in results)

    for check_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {check_name}")

    print()

    if all_passed:
        print("🎉 All checks passed! The scraper is ready to use.")
        print()
        print("Next steps:")
        print("  1. Run the test: python test_fetch_html.py")
        print("  2. Or try an example: python example_single_vendor.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print()
        print("Common fixes:")
        print("  - Install missing packages: pip install -r requirements.txt")
        print("  - Install Chrome: https://www.google.com/chrome/")
        print("  - Check Python version: python3 --version")

    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
