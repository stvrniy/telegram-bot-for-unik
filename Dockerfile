# Telegram Bot Dockerfile
FROM python:3.11-slim

# Metadata
LABEL maintainer="developer@email.com"
LABEL description="Telegram Educational Bot"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BOT_DIR=/opt/telegram-bot

# Set working directory
WORKDIR ${BOT_DIR}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash botuser

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p data logs backups && chown -R botuser:botuser ${BOT_DIR}

# Switch to non-root user
USER botuser

# Expose port (if webhook is used)
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "main.py"]
