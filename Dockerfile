# Use lightweight Python 3.11 base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Berlin \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (cron, tzdata, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    curl \
    ca-certificates \
    && ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY app.py ./
COPY downloader.py ./
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x ./scripts/entrypoint.sh

# Expose Marimo dashboard default port
EXPOSE 8501

# Volume for SQLite database and cached assets
VOLUME ["/app/data"]

# Entrypoint manages cron scheduler and starts Marimo dashboard
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
