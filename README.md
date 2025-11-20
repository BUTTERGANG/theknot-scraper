# TheKnot Scraper - Production-Ready Web Scraping Suite

Advanced web scraper for TheKnot.com with sophisticated bot detection bypass, comprehensive testing, and production deployment support.

## 🎯 Project Overview

This project provides a complete web scraping solution for extracting vendor information from TheKnot.com while bypassing multi-layered bot detection mechanisms.

### What's Included

- **Bot Detection Analysis** - Comprehensive analysis of TheKnot's security measures
- **Advanced Scraper** - Production-ready scraper with anti-detection
- **Testing Suite** - Unit tests, integration tests, and validation tools
- **Docker Support** - Containerized deployment
- **Documentation** - Extensive guides and references

## 📁 Project Structure

```
.
├── theknot_scraper/              # Main package
│   ├── scraper.py                # Core scraper implementation
│   ├── config.py                 # Configuration management
│   ├── utils.py                  # Utility functions
│   ├── test_fetch_html.py        # Integration test script
│   ├── validate_setup.py         # Setup validator
│   ├── example_single_vendor.py  # Single vendor example
│   ├── example_multiple_vendors.py  # Batch scraping example
│   └── README.md                 # Package documentation
│
├── tests/                        # Unit test suite
│   ├── test_config.py            # Configuration tests
│   ├── test_utils.py             # Utility function tests
│   └── conftest.py               # Pytest fixtures
│
├── Documentation/
│   ├── theknot-bot-detection-report.md  # Security analysis
│   ├── SCRAPER_DESIGN.md                # Architecture docs
│   ├── IMPLEMENTATION_NOTES.md          # Implementation guide
│   ├── SYSTEMATIC_IMPROVEMENTS.md       # Improvement analysis
│   └── ENHANCEMENTS_SUMMARY.md          # Enhancement summary
│
├── pyproject.toml                # Python package configuration
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Docker Compose configuration
├── Makefile                      # Common commands
├── .pre-commit-config.yaml       # Code quality hooks
└── README.md                     # This file
```

## 🚀 Quick Start

### Option 1: Traditional Installation

```bash
# Clone repository
git clone <repo-url>
cd theknot-scraper

# Install package
make install

# Or manually:
pip install -e .

# Validate setup
make validate

# Run integration test
cd theknot_scraper && python test_fetch_html.py
```

### Option 2: Docker (Recommended for Production)

```bash
# Build Docker image
make docker-build

# Or manually:
docker build -t theknot-scraper .

# Run with docker-compose
make docker-run

# Or manually:
docker-compose up

# View logs
make docker-logs
```

### Option 3: Development Setup

```bash
# Install with dev dependencies
make install-dev

# This installs:
# - pytest, pytest-cov (testing)
# - mypy (type checking)
# - black, ruff (formatting/linting)
# - pre-commit (git hooks)

# Run tests
make test

# Run with coverage
make test-cov

# Format code
make format

# Lint code
make lint
```

## 📖 Usage

### Basic Scraping

```python
from theknot_scraper import TheKnotScraper, ScraperConfig

# Configure
config = ScraperConfig(
    headless=False,  # Visible browser (recommended)
    min_delay=5.0,
    max_delay=10.0
)

# Scrape single vendor
with TheKnotScraper(config) as scraper:
    data = scraper.scrape_vendor_page(vendor_url)

    print(f"Business: {data.business_name}")
    print(f"Price: {data.starting_price}")
    print(f"Packages: {len(data.packages)}")
```

### Using Docker

```bash
# Edit environment variables
cp theknot_scraper/.env.example theknot_scraper/.env
nano theknot_scraper/.env

# Run with custom settings
HEADLESS=false MIN_DELAY=5.0 docker-compose up

# Run multiple workers
docker-compose up --scale scraper=3
```

## 🧪 Testing

### Run All Tests

```bash
make test
```

### Run with Coverage

```bash
make test-cov
# Opens htmlcov/index.html
```

### Run Integration Test

```bash
make test-integration
# Or:
cd theknot_scraper && python test_fetch_html.py
```

### Validate Setup

```bash
make validate
# Or:
cd theknot_scraper && python validate_setup.py
```

## 🛠️ Development

### Setup Development Environment

```bash
make dev-setup
```

This will:
- Install package in editable mode
- Install dev dependencies
- Set up pre-commit hooks
- Create necessary directories
- Copy .env.example to .env

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Available Make Commands

```bash
make help  # Show all available commands
```

Commands include:
- `install` - Install package
- `install-dev` - Install with dev dependencies
- `test` - Run unit tests
- `test-cov` - Run tests with coverage
- `lint` - Run linters
- `format` - Format code
- `clean` - Remove build artifacts
- `docker-build` - Build Docker image
- `docker-run` - Run in Docker
- `validate` - Validate setup

## 📊 Key Features

### Anti-Detection Measures

✅ **TLS Fingerprinting Bypass** - Real Chrome browser
✅ **JavaScript Patches** - 8+ stealth patches
✅ **Human Behavior Simulation** - Mouse, scrolling, timing
✅ **Session Management** - Cookie persistence
✅ **Retry Logic** - Automatic retry with backoff
✅ **Proxy Support** - HTTP/SOCKS proxies

### Testing & Quality

✅ **Unit Tests** - Fast, isolated tests
✅ **Integration Tests** - Live website testing
✅ **Type Checking** - MyPy type hints
✅ **Code Formatting** - Black + Ruff
✅ **Pre-commit Hooks** - Automated quality checks
✅ **Coverage Reports** - Track test coverage

### Deployment & Operations

✅ **Docker Support** - Containerized deployment
✅ **Docker Compose** - Multi-container orchestration
✅ **Health Checks** - Container health monitoring
✅ **Resource Limits** - CPU/memory constraints
✅ **Volume Mounts** - Persistent data storage

## 🔧 Configuration

### Environment Variables

All settings can be configured via environment variables:

```bash
# Browser settings
THEKNOT_HEADLESS=false
THEKNOT_WINDOW_SIZE=1920,1080

# Timing
THEKNOT_MIN_DELAY=5.0
THEKNOT_MAX_DELAY=10.0

# Behavior
THEKNOT_ENABLE_MOUSE_MOVEMENT=true
THEKNOT_ENABLE_RANDOM_SCROLLING=true

# Proxy
THEKNOT_PROXY=http://user:pass@proxy.com:8080

# Output
THEKNOT_OUTPUT_DIR=./output
THEKNOT_LOG_LEVEL=INFO
```

See `theknot_scraper/.env.example` for all options.

## 📈 Success Metrics

### Expected Success Rates

| Configuration | Success Rate | Notes |
|---------------|--------------|-------|
| Visible + Residential IP + Delays | 90-95% | Best setup |
| Visible + Home IP + Delays | 80-90% | Good |
| Visible + Datacenter IP | 40-60% | May fail |
| Headless + Any IP | 10-30% | Not recommended |

## 📚 Documentation

### Quick References

- **QUICKSTART.md** - 5-minute quick start
- **QUICK_TEST.md** - Quick test reference card
- **TESTING.md** - Complete testing guide

### Technical Documentation

- **theknot-bot-detection-report.md** - Security analysis (9/10 difficulty)
- **SCRAPER_DESIGN.md** - Architecture and design decisions
- **IMPLEMENTATION_NOTES.md** - Implementation guide for architects
- **SYSTEMATIC_IMPROVEMENTS.md** - Analysis of potential improvements

### Package Documentation

- **theknot_scraper/README.md** - Main package documentation
- Full troubleshooting guide
- Configuration options
- Example usage

## ⚖️ Legal & Ethical Considerations

**IMPORTANT:** This tool is for **educational and research purposes only**.

Before using:
1. ✅ Review TheKnot's Terms of Service
2. ✅ Respect robots.txt
3. ✅ Implement rate limiting (5-10s delays)
4. ✅ Consider official API for commercial use
5. ✅ Use responsibly and ethically

**We are not responsible for misuse of this tool.**

## 🐛 Troubleshooting

### Common Issues

**403 Forbidden:**
- Use residential proxy
- Increase delays to 10-15s
- Ensure `headless=False`

**CAPTCHA Challenges:**
- Solve manually (60s wait time)
- Reduce request rate
- Use different IP

**Import Errors:**
- Run scripts from `theknot_scraper/` directory
- Ensure package is installed: `pip install -e .`

**Docker Issues:**
- Check Chrome installation: `docker run theknot-scraper google-chrome --version`
- Verify volumes are mounted correctly
- Check logs: `docker-compose logs`

See `TESTING.md` for complete troubleshooting guide.

## 🤝 Contributing

### Development Workflow

1. Create feature branch
2. Make changes
3. Run tests: `make test`
4. Format code: `make format`
5. Run linters: `make lint`
6. Commit (pre-commit hooks run automatically)
7. Submit PR

### Testing Requirements

- Unit test coverage >85%
- All linters pass
- Type checking passes
- Integration test succeeds

## 📦 Dependencies

### Required

- Python 3.8+
- Chrome/Chromium browser
- undetected-chromedriver
- selenium
- pydantic
- loguru

### Optional (Development)

- pytest (testing)
- mypy (type checking)
- black (formatting)
- ruff (linting)
- pre-commit (git hooks)

See `pyproject.toml` for complete list.

## 🔐 Security

### Best Practices

- Never commit `.env` files
- Use environment variables for sensitive data
- Rotate proxies regularly
- Monitor for IP bans
- Respect rate limits

### Proxy Recommendations

✅ **Residential proxies** - Best success rate
⚠️ **Datacenter proxies** - Often blocked
❌ **Free proxies** - Very unreliable

## 📞 Support

### Getting Help

1. Check documentation in `theknot_scraper/README.md`
2. Review `TESTING.md` for troubleshooting
3. Check `IMPLEMENTATION_NOTES.md` for technical details
4. Review test examples in `tests/`

### Reporting Issues

Include:
- Python version
- Chrome version
- Configuration used
- Error messages
- Log output
- Screenshots if applicable

## 📝 License

MIT License - See LICENSE file for details

## 🎉 Acknowledgments

Built with:
- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [Selenium](https://www.selenium.dev/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
- [Loguru](https://github.com/Delgan/loguru)

---

**Version:** 1.0.0
**Status:** Production Ready
**Last Updated:** 2025-11-20

**Remember:** Use responsibly. Respect website policies and rate limits. Always implement appropriate delays.
