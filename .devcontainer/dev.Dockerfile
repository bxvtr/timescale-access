FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Disable output buffering
ENV PYTHONUNBUFFERED=1

# Install system packages required for TimescaleDB/PostgreSQL access etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libpq-dev \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create and prepare virtual environment
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip

ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Do NOT copy the source code here.
# The project directory will be mounted into /app by docker-compose.
