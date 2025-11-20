# Multi-stage Dockerfile for TheKnot Scraper
# Optimized for size and security

# Stage 1: Base image with Chrome
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Verify Chrome installation
RUN google-chrome --version

# Stage 2: Application
FROM base as app

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 scraper && \
    chown -R scraper:scraper /app

# Copy requirements first for better caching
COPY --chown=scraper:scraper requirements.txt pyproject.toml ./
COPY --chown=scraper:scraper theknot_scraper/requirements.txt ./theknot_scraper/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r theknot_scraper/requirements.txt

# Copy application code
COPY --chown=scraper:scraper theknot_scraper/ ./theknot_scraper/
COPY --chown=scraper:scraper README.md ./

# Create necessary directories
RUN mkdir -p /app/output /app/logs /app/cookies && \
    chown -R scraper:scraper /app/output /app/logs /app/cookies

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    THEKNOT_OUTPUT_DIR=/app/output \
    THEKNOT_LOG_FILE=/app/logs/scraper.log \
    THEKNOT_COOKIE_FILE=/app/cookies/cookies.pkl \
    # Chrome options for Docker
    CHROME_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu"

# Switch to non-root user
USER scraper

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from theknot_scraper import TheKnotScraper; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "theknot_scraper.example_single_vendor"]

# Build arguments for customization
ARG BUILD_DATE
ARG VERSION=1.0.0
ARG VCS_REF

# Labels
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="TheKnot Scraper" \
      org.opencontainers.image.description="Advanced web scraper for TheKnot.com with bot detection bypass" \
      org.opencontainers.image.authors="Security Research Team" \
      maintainer="research@example.com"
